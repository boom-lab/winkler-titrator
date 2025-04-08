from PyQt6.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QInputDialog, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal
import serial.tools.list_ports
import winkler
from model import serialDevices as sd
from model import iomod
from model import titration as ti
import numpy as np
import configparser
import sys
import os
import logging
from time import strftime, gmtime

# Set up root directory and config
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # Get project root directory
config = configparser.ConfigParser()

# Ensure config file exists and is readable
config_path = os.path.join(root_dir, 'wink.ini')
if not os.path.exists(config_path):
    raise FileNotFoundError(f"Config file not found at {config_path}")

config.read(config_path)
if not config.has_section('PUMP'):
    raise KeyError("Config file missing [PUMP] section")

Mthios = float(config['PUMP']['Mthios'])

# Set up logging
log_dir = os.path.join(root_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, f'log{strftime("%Y%m%d", gmtime())}.log'),
                   level='INFO',
                   format='%(levelname)s %(asctime)s %(message)s')
logging.info('Starting application')
logging.info(f"Pump controller: {config['PUMP']['Controller']}")

class runTitration(QThread):
    sig_done = pyqtSignal(bool)

    def __init__(self, titration, guess):
        """
        Make a new thread instance to run a titation without locking gui
        """
        super().__init__()
        self.current_titration = titration
        self.guess = np.float64(guess)

    def __del__(self):
        self.wait()

    def run(self):
        """
        start a titration (triggered by click of pushButton_titrate)
        """
        self.current_titration.start(self.guess)
        self.sig_done.emit(True)

class chartUpdater(QThread):
    sig_chart = pyqtSignal()
    sig_cumvol = pyqtSignal(int)

    def __init__(self, fpath):
        """
        Make a new thread instance to update chart without locking gui
        """
        super().__init__()
        self.fpath = fpath

    def __del__(self):
        self.wait()

    def run(self):
        """
        update chart (triggered by click of pushButton_titrate)
        """
        while True:
            self.sig_chart.emit()
            self.msleep(100)

class AppWindow(QMainWindow, winkler.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Winkler Titrator")
        
        # Connect signals
        self.pushButton_titrate.clicked.connect(self.titrate_clicked)
        self.pushButton_stop_titration.clicked.connect(self.stop_titration_clicked)
        self.pushButton_connect.clicked.connect(self.connect)
        self.pushButton_flask.clicked.connect(self.flask_clicked)
        self.pushButton_reload.clicked.connect(self.load_ports)
        
        # Initialize variables
        self.titr = None
        self.pump = None
        self.meter = None
        self.standard = None
        self.flask_calibration = None
        
        # Load ports
        self.load_ports()
        
        # Set up chart
        self.plot_data()

    def plot_data(self):
        """
        Set up the initial plot
        """
        self.widget_MPL.canvas.ax.clear()
        self.widget_MPL.canvas.ax.set_xlabel('Volume (uL)')
        self.widget_MPL.canvas.ax.set_ylabel('Potential (mV)')
        self.widget_MPL.canvas.draw()

    def connect(self):
        """
        Connect to selected devices
        """
        try:
            # Get debug mode setting
            debug_mode = self.checkBox_debug.isChecked()
            
            # Connect to meter
            meter_port = self.comboBox_meter.currentText()
            if meter_port:
                self.meter = sd.meter(meter_port, debug=debug_mode)
                if debug_mode:
                    logging.info(f"Connected to meter in DEBUG mode")
                else:
                    logging.info(f"Connected to meter on {meter_port}")
            
            # Connect to main pump based on config
            pump_port = self.comboBox_pump.currentText()
            if pump_port:
                pump_type = config.get('Pump', 'type', fallback='MFORCE').upper()
                if pump_type == 'MFORCE':
                    self.pump = sd.mforce_pump(pump_port, debug=debug_mode)
                else:
                    raise ValueError(f"Unsupported pump type: {pump_type}")
                
                if debug_mode:
                    logging.info(f"Connected to {pump_type} pump in DEBUG mode")
                else:
                    logging.info(f"Connected to {pump_type} pump on {pump_port}")
            
            # Connect to standard pump based on config
            standard_port = self.comboBox_standard.currentText()
            if standard_port:
                standard_type = config.get('Standard', 'type', fallback='MFORCE').upper()
                if standard_type == 'MFORCE':
                    self.standard = sd.mforce_pump(standard_port, debug=debug_mode)
                else:
                    raise ValueError(f"Unsupported standard pump type: {standard_type}")
                
                if debug_mode:
                    logging.info(f"Connected to {standard_type} standard pump in DEBUG mode")
                else:
                    logging.info(f"Connected to {standard_type} standard pump on {standard_port}")
            
            if self.meter and self.pump and self.standard:
                if debug_mode:
                    QMessageBox.information(self, "Success", "All devices connected in DEBUG mode!")
                else:
                    QMessageBox.information(self, "Success", "All devices connected successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Some devices failed to connect")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect: {str(e)}")
            logging.error(f"Connection error: {str(e)}")

    def flask_clicked(self):
        """
        Handle flask calibration file selection
        """
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flask Calibration File",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if filename:
            self.load_flask_calibration(filename)

    def load_flask_calibration(self, filename):
        """
        Load flask calibration data from CSV file
        """
        try:
            self.flask_calibration = iomod.import_flasks(filename)
            if not self.flask_calibration:
                raise ValueError("No flask calibration data found in file")
                
            self.comboBox_flasks.clear()
            self.comboBox_flasks.addItems(sorted(self.flask_calibration.keys()))
            logging.info(f"Loaded {len(self.flask_calibration)} flasks from {filename}")
            QMessageBox.information(
                self,
                "Success",
                f"Successfully loaded {len(self.flask_calibration)} flask calibrations"
            )
        except Exception as e:
            self.flask_calibration = None
            self.comboBox_flasks.clear()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load flask calibration:\n{str(e)}"
            )
            logging.error(f"Flask calibration error: {str(e)}")

    def load_ports(self):
        """
        Load available COM ports
        """
        ports = getPorts()
        self.comboBox_meter.clear()
        self.comboBox_pump.clear()
        self.comboBox_standard.clear()
        
        for port in ports:
            self.comboBox_meter.addItem(port)
            self.comboBox_pump.addItem(port)
            self.comboBox_standard.addItem(port)

    def get_metadata_log(self):
        """
        Get metadata for logging
        """
        return {
            'id': self.lineEdit_id.text(),
            'thio_t': self.doubleSpinBox_thio_t.value(),
            'kio3_t': self.doubleSpinBox_kio3_temp.value(),
            'flask': self.comboBox_flasks.currentText()
        }

    def get_titration_type(self):
        """
        Get selected titration type
        """
        if self.pushButton_sample_type.isChecked():
            return 'sample'
        elif self.pushButton_standard_type.isChecked():
            return 'standard'
        elif self.pushButton_sea_water_blank_type.isChecked():
            return 'sea_water_blank'
        elif self.pushButton_di_water_blank_type.isChecked():
            return 'di_water_blank'
        return 'sample'

    def titrate_clicked(self):
        """
        Start titration process
        """
        if not (self.meter and self.pump):
            QMessageBox.warning(self, "Error", "Please connect to meter and pump first")
            return

        try:
            # Get titration parameters
            guess = self.spinBox_guess.value()
            metadata = self.get_metadata_log()
            titration_type = self.get_titration_type()
            
            # Get flask calibration values
            selected_flask = self.comboBox_flasks.currentText()
            if not selected_flask or not self.flask_calibration:
                raise ValueError("No flask calibration data loaded. Please load flask calibration file first.")
            
            flask_volume = self.flask_calibration.get(selected_flask)
            if flask_volume is None:
                raise ValueError(f"Flask {selected_flask} not found in calibration data")
            
            # Initialize titration
            self.titr = ti.titration(
                meter=self.meter,
                pump=self.pump,
                botid=selected_flask,  # Use selected flask ID
                vbot=flask_volume,  # Use calibrated flask volume
                type=titration_type,
                Mthios=float(config.get('Pump', 'Mthios', fallback='0.200')),  # Get Mthios from config
                thio_t=25.0,  # Default thiosulfate temperature in °C
                mode='normal'  # Default mode
            )
            
            # Debug mode is already set in the meter and pump objects
            
            # Start titration thread
            self.titration_thread = runTitration(self.titr, guess)
            self.titration_thread.sig_done.connect(self.titration_done)
            self.titration_thread.start()
            
            # Start chart update thread
            self.chart_thread = chartUpdater(self.titr.fpath)
            self.chart_thread.sig_chart.connect(self.show_titration_result)
            self.chart_thread.start()
            
            # Update UI
            self.pushButton_titrate.setEnabled(False)
            self.pushButton_stop_titration.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start titration: {str(e)}")
            logging.error(f"Titration error: {str(e)}")

    def stop_titration_clicked(self):
        """
        Stop titration process
        """
        if self.titr:
            self.titr.stop()
            self.pushButton_titrate.setEnabled(True)
            self.pushButton_stop_titration.setEnabled(False)
            if self.chart_thread:
                self.chart_thread.terminate()

    def titration_done(self):
        """
        Handle titration completion
        """
        self.pushButton_titrate.setEnabled(True)
        self.pushButton_stop_titration.setEnabled(False)
        if self.chart_thread:
            self.chart_thread.terminate()
        
        endpoint = self.titr.endpoint
        QMessageBox.information(self, "Complete", f"Titration complete: endpoint = {endpoint:.2f} uL")

    def dispense_standard_clicked(self):
        """
        Dispense standard solution
        """
        if self.standard:
            vol = self.spinBox_standard.value()
            self.dispense_vol(self.standard, vol)

    def load_standard_clicked(self):
        """
        Load standard solution
        """
        if self.standard:
            self.standard.load()

    def empty_standard_clicked(self):
        """
        Empty standard solution
        """
        if self.standard:
            self.standard.empty()

    def fill_standard_clicked(self):
        """
        Fill standard solution
        """
        if self.standard:
            self.standard.fill()

    def dispense_thios_clicked(self):
        """
        Dispense thiosulfate solution
        """
        if self.pump:
            vol = self.spinBox_thios.value()
            self.dispense_vol(self.pump, vol)

    def load_thios_clicked(self):
        """
        Load thiosulfate solution
        """
        if self.pump:
            self.pump.load()

    def dispense_vol(self, pump, vol):
        """
        Dispense specified volume
        """
        try:
            pump.dispense(vol)
            logging.info(f"Dispensed {vol} uL")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to dispense: {str(e)}")
            logging.error(f"Dispense error: {str(e)}")

    def dispense_1uL(self):
        self.dispense_vol(self.pump, 1)

    def dispense_10uL(self):
        self.dispense_vol(self.pump, 10)

    def dispense_100uL(self):
        self.dispense_vol(self.pump, 100)

    def dispense_1000uL(self):
        self.dispense_vol(self.pump, 1000)

    def dispense_5000uL(self):
        self.dispense_vol(self.pump, 5000)

    def show_titration_result(self):
        """
        Update the plot with titration results
        """
        if self.titr and hasattr(self.titr, 'data'):
            self.widget_MPL.canvas.ax.clear()
            self.widget_MPL.canvas.ax.plot(self.titr.data['vol'], self.titr.data['pot'])
            self.widget_MPL.canvas.ax.set_xlabel('Volume (uL)')
            self.widget_MPL.canvas.ax.set_ylabel('Potential (mV)')
            self.widget_MPL.canvas.draw()
            self.lcdNumber_dispensed.display(self.titr.data['vol'][-1])
            self.lcdNumber_endpoint.display(self.titr.endpoint)

def getPorts():
    """
    Get list of available COM ports
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append(port.device)
    return ports

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())
