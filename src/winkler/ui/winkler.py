import sys
import os
import logging
from time import strftime, gmtime
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox,
    QInputDialog, QLineEdit
)
from PyQt6.QtCore import QThread, pyqtSignal
import serial.tools.list_ports
import numpy as np
import configparser

from ..model import serialDevices as sd
from ..model import iomod
from ..model import titration as ti
from .ui_main import Ui_MainWindow

# Setup configuration
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
config = configparser.ConfigParser()
config.read(os.path.join(root_dir, 'wink.ini'))
Mthios = config['PUMP']['Mthios']

# Setup logging
logging.basicConfig(
    filename=os.path.join(root_dir, 'log' + strftime("%Y%m%d", gmtime())),
    level='INFO',
    format='%(levelname)s %(asctime)s %(message)s'
)
logging.info('Starting application')
logging.info(f"Pump controller: {config['PUMP']['Controller']}")

class RunTitration(QThread):
    """Thread for running titration without blocking GUI"""
    sig_done = pyqtSignal(bool)

    def __init__(self, titration, guess):
        super().__init__()
        self.current_titration = titration
        self.guess = float(guess)

    def run(self):
        """Start a titration (triggered by click of pushButton_titrate)"""
        self.current_titration.titrate(self.guess)
        self.sig_done.emit(True)

class ChartUpdater(QThread):
    """Thread for updating chart in real-time"""
    sig_chart = pyqtSignal()
    sig_cumvol = pyqtSignal(int)

    def __init__(self, fpath):
        super().__init__()
        self.filename = fpath
        self.filesize = 0
        if os.path.exists(self.filename):
            self.filesize = os.path.getsize(self.filename)

    def run(self):
        """Update chart when file changes"""
        while True:
            if os.path.exists(self.filename) and os.path.getsize(self.filename) > self.filesize:
                self.filesize = os.path.getsize(self.filename)
                self.sig_chart.emit()

class AppWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        #self.ui.widget_MPL.addWidget(self.canvas)
        self.pushButton_connect.clicked.connect(self.connect)
        self.pushButton_reload.clicked.connect(self.load_ports)
        self.pushButton_flask.clicked.connect(self.flask_clicked)
        self.pushButton_titrate.clicked.connect(self.titrate_clicked)
        self.pushButton_stop_titration.clicked.connect(self.stop_titration_clicked)
        self.pushButton_dispenseStandard.clicked.connect(self.dispense_standard_clicked)
        self.pushButton_loadStandard.clicked.connect(self.load_standard_clicked)
        self.pushButton_emptyStandard.clicked.connect(self.empty_standard_clicked)
        self.pushButton_fillStandard.clicked.connect(self.fill_standard_clicked)
        self.pushButton_dispenseThios.clicked.connect(self.dispense_thios_clicked)
        self.pushButton_loadThios.clicked.connect(self.load_thios_clicked)
        #self.comboBox_meter.activated.connect(self.load_ports)
        #self.comboBox_pump.activated.connect(self.load_ports)
        # Connect dispense buttons
        self.pushButton_1uL.clicked.connect(lambda: self.dispense_vol(1))
        self.pushButton_10uL.clicked.connect(lambda: self.dispense_vol(10))
        self.pushButton_100uL.clicked.connect(lambda: self.dispense_vol(100))
        self.pushButton_1000uL.clicked.connect(lambda: self.dispense_vol(1000))
        self.pushButton_5000uL.clicked.connect(lambda: self.dispense_vol(5000))
        #self.pushButton_customvol.clicked.connect(self.dispense_custom)

        self.checkBox_gran.stateChanged.connect(self.plot_data)
        self.checkBox_zoom.stateChanged.connect(self.plot_data)
        self.checkBox_rapid.stateChanged.connect(self.update_titration_mode)

        #self.verticalSlider_standard.valueChanged.connect(self.lcdNumber_standard.display)

        self.load_ports()

        # Load flask calibration if available in configuration
        if 'FLASKS_CALIBRATION' in config and 'Path' in config['FLASKS_CALIBRATION']:
            print('Load flasks calibration from configuration')
            self.load_flask_calibration(config['FLASKS_CALIBRATION']['Path'])

    def update_titration_mode(self):
        """Update the titration mode based on the rapid mode checkbox"""
        if hasattr(self, 'titr'):
            self.titr.mode = 'rapid' if self.checkBox_rapid.isChecked() else 'normal'

    def plot_data(self):
        """Update plot with current titration data"""
        self.widget_MPL.canvas.ax.cla()
        self.widget_MPL.canvas.ax.grid()
        self.widget_MPL.canvas.ax.set_xlabel('µL')

        if hasattr(self, 'titr'):
            # Get the data arrays
            uL = self.titr.uL
            mV = self.titr.mV
            gF = self.titr.gF if hasattr(self.titr, 'gF') else None
            
            # Ensure we have data to plot
            if len(uL) == 0 or len(mV) == 0:
                self.widget_MPL.canvas.draw()
                return
                
            # Get the zoom range if zoom is enabled
            if self.checkBox_zoom.isChecked():
                d = np.where(np.abs(uL - self.titr.v_end) < 30)[0]
                if len(d) == 0:  # If no points in zoom range, use all points
                    d = np.arange(len(uL))
            else:
                d = np.arange(len(uL))
            
            # Plot the data
            if self.checkBox_gran.isChecked() and gF is not None:
                y = gF
                self.widget_MPL.canvas.ax.set_ylabel('gran factor')
            else:
                y = mV
                self.widget_MPL.canvas.ax.set_ylabel('mV')

            # Ensure indices are within bounds
            d = d[d < len(uL)]
            d = d[d < len(y)]
            
            if len(d) > 0:
                self.widget_MPL.canvas.ax.plot(uL[d], y[d], '.-')
                self.widget_MPL.canvas.ax.plot(uL[-1], y[-1], 'ro')
            
            self.widget_MPL.canvas.draw()
            self.lcdNumber_dispensed.display(self.titr.cumvol)
            self.lcdNumber_endpoint.display(self.titr.v_end)


    def connect(self):
        """Connect to meter and pump devices"""
        logging.info('Connecting serial devices')
        logging.info(f"Pump set to {config['PUMP']['Controller']}")
        logging.info(f"Meter set to {config['METER']['Series']}")

        # Connect meter
        try:
            meter_series = config['METER']['Series'].lower()
            if meter_series == 'atlas':
                self.meter = sd.meter(self.comboBox_meter.currentText())
            else:
                self.meter = sd.meter(
                    self.comboBox_meter.currentText(),
                    int(config['METER']['mVpos']),
                    int(config['METER']['Tpos'])
                )
            logging.info(f"Meter connected on {self.comboBox_meter.currentText()}")
        except Exception as ex:
            logging.warning(ex)
            QMessageBox.warning(
                self,
                'Connect Warning',
                'Meter connection failed',
                QMessageBox.StandardButton.Ok
            )

        # Connect main pump
        try:
            pump_controller = config['PUMP']['Controller']
            if pump_controller == 'MFORCE':
                self.pump = sd.mforce_pump(self.comboBox_pump.currentText())
            elif pump_controller == 'MLYNX':
                self.pump = sd.mlynx_pump(self.comboBox_pump.currentText())
            elif pump_controller == 'KLOEHN':
                self.pump = sd.kloehn_pump(
                    self.comboBox_pump.currentText(),
                    steps=config['PUMP']['Steps'],
                    syringe_vol=config['PUMP']['SyringeVol'],
                    VM=config['PUMP']['MaxVelocity'],
                    InAddr=config['PUMP']['InAddr'],
                    OutAddr=config['PUMP']['OutAddr'],
                    PumpAddr=config['PUMP']['PumpAddr']
                )
            logging.info(f"{pump_controller} pump connected on {self.comboBox_pump.currentText()}")
        except Exception as ex:
            logging.warning(f"Pump connection failed: {ex}")
            QMessageBox.warning(
                self,
                'Connect Warning',
                'Pump connection failed',
                QMessageBox.StandardButton.Ok
            )

        # Connect standard pump
        try:
            if self.comboBox_standard.currentText() == 'None':
                self.std_pump = None
                logging.info('No standard pump available')
            else:
                std_controller = config['STD_PUMP']['Controller']
                if std_controller == 'MFORCE':
                    self.std_pump = sd.mforce_pump(self.comboBox_standard.currentText())
                elif std_controller == 'MLYNX':
                    self.std_pump = sd.mlynx_pump(self.comboBox_standard.currentText())
                logging.info(f"Standard pump ({std_controller}) connected on {self.comboBox_standard.currentText()}")
        except Exception as ex:
            logging.warning(f"Standard pump connection failed: {ex}")
            self.std_pump = None


    def flask_clicked(self):
        """Handle flask calibration file selection"""
        logging.debug('Flask button clicked')
        filename, _ = QFileDialog.getOpenFileName(
            self,
            'Open Flask Calibration File',
            str(root_dir),
            'CSV files (*.csv)'
        )
        if filename:
            logging.debug(f'Selected file: {filename}')
            self.load_flask_calibration(filename)
        else:
            logging.debug('No file selected')

    def load_flask_calibration(self, filename):
        """Load flask calibration data"""
        logging.debug(f'Attempting to load flask calibration from {filename}')
        try:
            self.flask_calibration = iomod.import_flasks(filename)
            if not self.flask_calibration:
                raise ValueError("No calibration data found")
            logging.info(f"Loaded flask calibration from {filename}")
            
            # Update flask selection combo box
            self.comboBox_flasks.clear()
            self.comboBox_flasks.addItems(sorted(self.flask_calibration.keys()))
            logging.debug(f'Added {len(self.flask_calibration)} flasks to combo box')
            
        except Exception as ex:
            logging.error(f"Error loading flask calibration: {ex}")
            QMessageBox.warning(
                self,
                'Flask Calibration Error',
                str(ex),
                QMessageBox.StandardButton.Ok
            )

    def load_ports(self):
        """Load available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.comboBox_meter.clear()
        self.comboBox_pump.clear()
        self.comboBox_standard.clear()
        self.comboBox_meter.addItems(ports)
        self.comboBox_pump.addItems(ports)
        self.comboBox_standard.addItems(['None'] + ports)

        # If default connection listed in configuration
        if 'Port' in config['METER']:
            if config['METER']['Port'] in ports:
                self.comboBox_meter.setCurrentText(config['METER']['Port'])
        if 'Port' in config['PUMP']:
            if config['PUMP']['Port'] in ports:
                self.comboBox_pump.setCurrentText(config['PUMP']['Port'])
        if 'Port' in config['STD_PUMP']:
            if config['PUMP']['Port'] in ports or config['PUMP']['Port']=='None':
                self.comboBox_standard.setCurrentText(config['STD_PUMP']['Port'])

    # def get_metadata_log(self):
    #     """Get metadata for logging"""
    #     metadata = {
    #         'bottle': self.lineEdit_id.text() if hasattr(self, 'lineEdit_id') else '',
    #         'station': self.lineEdit_station.text() if hasattr(self, 'lineEdit_station') else '',
    #         'cast': self.lineEdit_cast.text() if hasattr(self, 'lineEdit_cast') else '',
    #         'niskin': self.lineEdit_niskin.text() if hasattr(self, 'lineEdit_niskin') else '',
    #         'lat': self.lineEdit_lat.text() if hasattr(self, 'lineEdit_lat') else '',
    #         'lon': self.lineEdit_lon.text() if hasattr(self, 'lineEdit_lon') else '',
    #         'depth': self.lineEdit_depth.text() if hasattr(self, 'lineEdit_depth') else ''
    #     }
    #     return metadata

    def get_titration_type(self):
        """Get the type of titration to perform"""
        if self.pushButton_sea_water_blank_type.isChecked():
            return 'blank'
        elif self.pushButton_standard_type.isChecked():
            return 'standard'
        return 'sample'

    def titrate_clicked(self):
        """Start a titration"""
        try:
            titration_type = self.get_titration_type()
            
            # Get the bottle ID and look up its volume
            botid = self.comboBox_flasks.currentText()
            if not hasattr(self, 'flask_calibration'):
                raise ValueError("No flask calibration loaded")
            if botid not in self.flask_calibration:
                raise ValueError(f"Bottle ID {botid} not found in calibration data")
            vbot = self.flask_calibration[botid]
            
            # Determine titration mode
            mode = 'rapid' if self.checkBox_rapid.isChecked() else 'normal'
            
            self.titr = ti(
                self.meter,
                self.pump,
                botid,  # botid - keep as string
                vbot,   # vbot - already a float from calibration
                titration_type,  # type
                float(config['PUMP']['Mthios']),  # Mthios
                float(self.doubleSpinBox_thio_t.value()),  # thio_t
                mode=mode  # Use the mode from checkbox
            )
            
            # Set debug state from checkbox
            self.titr.pump.DEBUG = self.checkBox_pumpDebug.isChecked()
            
            self.tthread = RunTitration(self.titr, float(self.spinBox_guess.value()))
            self.tthread.sig_done.connect(self.titration_done)
            self.tthread.start()
            
            self.plt_thr = ChartUpdater(self.titr.current_file)
            self.plt_thr.sig_chart.connect(self.plot_data)
            self.plt_thr.start()
            
        except Exception as ex:
            logging.error(f"Titration failed: {ex}")
            QMessageBox.warning(
                self,
                'Titration Error',
                str(ex),
                QMessageBox.StandardButton.Ok
            )

    def stop_titration_clicked(self):
        """Stop the current titration"""
        if hasattr(self, 'titr'):
            self.titr.stop()
            logging.info('Titration stopped by user')

    def titration_done(self):
        """Handle completion of titration"""
        self.plot_data()
        self.show_titration_result()

    def show_titration_result(self):
        """Display titration results"""
        if hasattr(self, 'titr'):
            result = (
                f"Titration complete\n"
                f"Endpoint: {self.titr.v_end:.2f} µL\n"
                #f"O2: {self.titr.O2:.2f} µmol/kg"
            )
            QMessageBox.information(
                self,
                'Titration Result',
                result,
                QMessageBox.StandardButton.Ok
            )

    def dispense_vol(self, vol):
        """Dispense a specific volume"""
        if self.pump:
            try:
                self.pump.dispense(vol)
                logging.info(f"Dispensed {vol} µL")
            except Exception as ex:
                logging.error(f"Error dispensing volume: {ex}")
                QMessageBox.warning(
                    self,
                    'Dispense Error',
                    str(ex),
                    QMessageBox.StandardButton.Ok
                )

    def dispense_standard_clicked(self):
        """Dispense standard solution"""
        if self.std_pump:
            vol = float(self.lineEdit_standardVol.text())
            self.std_pump.dispense(vol)
            logging.info(f"Dispensed {vol} µL of standard")

    def load_standard_clicked(self):
        """Load standard solution"""
        if self.std_pump:
            self.std_pump.load()
            logging.info('Loading standard solution')

    def empty_standard_clicked(self):
        """Empty standard solution"""
        if self.std_pump:
            self.std_pump.empty()
            logging.info('Emptying standard solution')

    def fill_standard_clicked(self):
        """Fill standard solution"""
        if self.std_pump:
            self.std_pump.fill()
            logging.info('Filling standard solution')

    def dispense_thios_clicked(self):
        """Dispense thiosulfate solution"""
        if self.pump:
            vol = float(self.lineEdit_thiosVol.text())
            self.pump.dispense(vol)
            logging.info(f"Dispensed {vol} µL of thiosulfate")

    def load_thios_clicked(self):
        """Load thiosulfate solution"""
        if self.pump:
            self.pump.load()
            logging.info('Loading thiosulfate solution')


def getPorts():
    ports = serial.tools.list_ports.comports()
    if not ports:
        return ("No Serial Port Detected",'This is not a port')
    else:
        return ports

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())
