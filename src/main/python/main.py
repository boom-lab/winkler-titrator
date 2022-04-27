from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow

import sys
import os
import logging
from time import strftime,gmtime
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog,QMessageBox, QInputDialog,QLineEdit
from PyQt5.QtCore import QThread,pyqtSignal
import serial.tools.list_ports
import winkler
from model import serialDevices as sd
from model import iomod
from model import titration as ti
import numpy as np
import configparser


#Mthios = float(config.Mthios)
root_dir = os.path.join(os.path.expanduser('~'),'winkler-titrator-hakai')
config = configparser.ConfigParser()
config.read(os.path.join(root_dir,'wink.ini'))
Mthios = config['PUMP']['Mthios']

#print('in address is :' + config['PUMP']['InAddr'])

logging.basicConfig(filename=os.path.join(root_dir,'log'+strftime("%Y%m%d", \
    gmtime())),level='INFO',format='%(levelname)s %(asctime)s %(message)s')
logging.info('Im logging!')
logging.info(config['PUMP']['Controller'])

class runTitration(QThread):

    sig_done = pyqtSignal(bool)

    def __init__(self, titration, guess):
        """
        Make a new thread instance to run a titation without locking gui
        """
        QThread.__init__(self)
        self.current_titration = titration
        self.guess = np.float(guess)


    def __del__(self):
        self.wait()

    def run(self):
        """
        start a titration (triggered by click of pushButton_titrate)
        """
        self.current_titration.titrate(self.guess)
        self.sig_done.emit(True)

class chartUpdater(QThread):

    sig_chart = pyqtSignal()
    sig_cumvol = pyqtSignal(int)

    def __init__(self, fpath):
        """
        loads latest titration data from file and send to plot
        """
        QThread.__init__(self)
        self.filename = fpath
        self.filesize = os.path.getsize(self.filename)
        self.sig_chart.connect
        self.sig_cumvol.connect


    def __del__(self):
        self.wait()

    def run(self):
        """
        start a titration (triggered by click of pushButton_titrate)
        """
        while True:
            if os.path.getsize(self.filename) > self.filesize:
                self.filesize = os.path.getsize(self.filename)
                self.sig_chart.emit()


class AppWindow(QMainWindow,winkler.Ui_MainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
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
        self.pushButton_1uL.clicked.connect(self.dispense_1uL)
        self.pushButton_10uL.clicked.connect(self.dispense_10uL)
        self.pushButton_100uL.clicked.connect(self.dispense_100uL)
        self.pushButton_1000uL.clicked.connect(self.dispense_1000uL)
        self.pushButton_5000uL.clicked.connect(self.dispense_5000uL)
        #self.pushButton_customvol.clicked.connect(self.dispense_custom)

        self.checkBox_gran.stateChanged.connect(self.plot_data)
        self.checkBox_zoom.stateChanged.connect(self.plot_data)

        #self.verticalSlider_standard.valueChanged.connect(self.lcdNumber_standard.display)

        self.load_ports()

        # Load flask calibration if available in configuration
        if 'FLASKS_CALIBRATION' in config and 'Path' in config['FLASKS_CALIBRATION']:
            print('Load flasks calibration from configuration')
            self.load_flask_calibration(config['FLASKS_CALIBRATION']['Path'])


    def plot_data(self):

        self.widget_MPL.canvas.ax.cla()
        self.widget_MPL.canvas.ax.grid()
        self.widget_MPL.canvas.ax.set_xlabel('uL')

        if hasattr(self,'titr'):
            if self.checkBox_zoom.isChecked():
                d = np.where(np.abs(self.titr.uL-self.titr.v_end) < 30)
            else:
                d = range(len(self.titr.uL))
            if self.checkBox_gran.isChecked():
                y = self.titr.gF
                self.widget_MPL.canvas.ax.set_ylabel('gran factor')
            else:
                y = self.titr.mV
                self.widget_MPL.canvas.ax.set_ylabel('mV')

            self.widget_MPL.canvas.ax.plot(self.titr.uL[d],y[d],'.-')
            self.widget_MPL.canvas.ax.plot(self.titr.uL[-1],y[-1],'ro')
            self.widget_MPL.canvas.draw()
            self.lcdNumber_dispensed.display(self.titr.cumvol)
            self.lcdNumber_endpoint.display(self.titr.v_end)


    def connect(self):
        #if not (hasattr(self,'pump') and hasattr(self,'meter')):
        #    self.load_ports()
        #print(self.comboBox_meter.currentText())
        #print(self.comboBox_pump.currentText())
        logging.info('connecting serial devices')
        logging.info('pump set to ' + config['PUMP']['Controller'])
        logging.info('meter set to ' + config['METER']['Series'])
        try:
            self.meter = sd.meter(self.comboBox_meter.currentText(),int(config['METER']['mVpos']),int(config['METER']['Tpos']))
            logging.info('meter connected on ' + self.comboBox_meter.currentText())
        except Exception as ex:
            logging.warning(ex)
            QMessageBox.warning(self,'Connect Warning',\
                                'Meter connection failed',QMessageBox.Ok)
        try:
            print ('connecting ' + config['PUMP']['Controller'] + ' series pump')
            if config['PUMP']['Controller'] == 'MFORCE':
                self.pump = sd.mforce_pump(self.comboBox_pump.currentText())
                logging.info('MFORCE pump connected on ' + self.comboBox_pump.currentText())
            elif config['PUMP']['Controller'] == 'MLYNX':
                self.pump = sd.mlynx_pump(self.comboBox_pump.currentText())
                logging.info('MLYNX pump connected on ' + self.comboBox_pump.currentText())
            elif config['PUMP']['Controller'] == 'KLOEHN':
                vm = config['PUMP']['MaxVelocity']
                svol = config['PUMP']['SyringeVol']
                steps = config['PUMP']['Steps']
                inaddr = config['PUMP']['InAddr']
                outaddr = config['PUMP']['OutAddr']
                pumpaddr = config['PUMP']['PumpAddr']
                self.pump = sd.kloehn_pump(self.comboBox_pump.currentText(),steps=steps,syringe_vol=svol,VM=vm,InAddr=inaddr,OutAddr=outaddr,PumpAddr=pumpaddr)
                logging.info('KLOEHN pump connected on ' + self.comboBox_pump.currentText())

        except Exception as ex:
            QMessageBox.warning(self,'Connect Warning',\
                                'Pump connection failed',QMessageBox.Ok)
            logging.warning('Pump connection failed')
            logging.warning(ex)

        # Connect pump for dispensing standard (KIO3)
        try:
            if self.comboBox_standard.currentText()=='None':
                self.std_pump = None
                logging.info('No standard pump available')
            elif config['STD_PUMP']['Controller'] == 'MFORCE':
                self.std_pump = sd.mforce_pump(self.comboBox_standard.currentText())
                logging.info('MFORCE pump connected on ' + self.comboBox_standard.currentText())
            elif config['STD_PUMP']['Controller'] == 'MLYNX':
                self.std_pump = sd.mlynx_pump(self.comboBox_standard.currentText())
                logging.info('MLYNX pump connected on ' + self.comboBox_standard.currentText())
            elif config['STD_PUMP']['Controller'] == 'KLOEHN':
                vm = config['STD_PUMP']['MaxVelocity']
                svol = config['STD_PUMP']['SyringeVol']
                steps = config['STD_PUMP']['Steps']
                inaddr = config['STD_PUMP']['InAddr']
                outaddr = config['STD_PUMP']['OutAddr']
                pumpaddr = config['STD_PUMP']['PumpAddr']
                self.std_pump = sd.kloehn_pump(self.comboBox_standard.currentText(),steps=steps,syringe_vol=svol,VM=vm,InAddr=inaddr,OutAddr=outaddr,PumpAddr=pumpaddr)
                logging.info('KLOEHN pump connected on ' + self.comboBox_standard.currentText()+'with '+ str(svol) + ' uL syringe')
        except Exception as ex:
            QMessageBox.warning(self,'Connect Warning',\
                            'Standard Pump connection failed',QMessageBox.Ok)
            logging.warning('Standard Pump connection failed')
            logging.warning(ex)


    def flask_clicked(self):
        filename = QFileDialog.getOpenFileName(None,'Test Dialog')
        logging.info('bottle file '+filename[0]+ ' loaded')
        self.load_flask_calibration(filename[0])
        return filename

    def load_flask_calibration(self,filename):
        self.botdict = iomod.import_flasks(filename)
        botid = sorted(self.botdict.keys())
        for bot in botid:
            self.comboBox_flasks.addItem(bot)

    def load_ports(self):
        self.comboBox_meter.clear()
        self.comboBox_pump.clear()
        self.comboBox_standard.clear()
        ports = serial.tools.list_ports.comports()
        device_list = []
        for p in ports:
            if True:#if 'usb' in p.device or 'COM' in p.device:
                self.comboBox_meter.addItem(p.device)
                self.comboBox_pump.addItem(p.device)
                self.comboBox_standard.addItem(p.device)
                device_list.append(p.device)
        self.comboBox_standard.addItem('None')
        print(config['METER']['Port'] in ports)
        
        # If default connection listed in configuration
        if 'Port' in config['METER'] and config['METER']['Port'] in device_list:
            self.comboBox_meter.setCurrentText(config['METER']['Port'])
        if 'Port' in config['PUMP'] and config['PUMP']['Port'] in device_list:
            self.comboBox_pump.setCurrentText(config['PUMP']['Port'])
        if 'Port' in config['STD_PUMP'] and config['PUMP']['Port'] in device_list or config['PUMP']['Port']=='None':
            self.comboBox_standard.setCurrentText(config['STD_PUMP']['Port'])

    def get_metadata_log(self):
        return {
            "kio3_temp": self.doubleSpinBox_kio3_temp
        }

    def get_titration_type(self):
        if self.pushButton_sample_type.isChecked():
            return 'sample'
        elif self.pushButton_standard_type.isChecked():
            return 'standard'
        elif self.pushButton_di_water_blank_type.isChecked():
            return 'di_blank'
        elif self.pushButton_sea_water_blank_type.isChecked():
            return 'sw_blank'

    def titrate_clicked(self):
        guess = float(self.spinBox_guess.value())
        self.lcdNumber_endpoint.display(0)
        self.lcdNumber_dispensed.display(0)
        logging.info('titration started with initial guess '+ str(guess))
        #print('initial guess is ' + str(guess))
        flaskid = self.comboBox_flasks.currentText()
        flaskvol = self.botdict[flaskid]
        titration_type = self.get_titration_type()
        thio_t = self.doubleSpinBox_thio_t.value()
        logging.info('Thiosulfate temperature = ' + str(thio_t) + ' degC' )
        logging.info('flask ' + flaskid + '[' + titration_type + '] with volume = ' + str(flaskvol) )
        #print('flask volume =' + str(flaskvol))
        if self.checkBox_rapid.isChecked():
            timode = 'rapid'
        else:
            timode = 'normal'
        #logging.info(str(timode))
        self.titr = ti.titration(self.meter,self.pump,flaskid,flaskvol,titration_type,0.2,thio_t,\
                            mode=timode)
        print('running titration')
        self.ti_thr = runTitration(self.titr,guess)
        self.ti_thr.start()
        self.plt_thr = chartUpdater(self.titr.current_file)
        self.plt_thr.sig_chart.connect(self.plot_data)
        #self.plt_thr.sig_cumvol.connect(self.lcdNumber_dispensed.value)
        self.plt_thr.start()
        self.ti_thr.finished.connect(self.titration_done)

    def stop_titration_clicked(self):
        if  hasattr(self, 'titr'):
            self.titr.run_titration = False
            logging.info('Titration manually stopped in progress')
        else:
            logging.info('Clicked "Stop Titration" but no titration is in progress')

    def titration_done(self):
        # QMessageBox.warning(self,'','titration complete: endpoint=' +  \
        #         str(self.titr.endpoint),QMessageBox.Ok)
        extra_metadata = self.get_metadata_log()
        comment, ok =  QInputDialog.getText(self,'Titration completed', 'Titration completed: endpoint=' +  \
                str(self.titr.endpoint) +'uL\nAdd a comment here:')
        self.titr.comment = comment
        self.titr.toJSON(extra_metadata)
        self.titr.pump.fill()

    def dispense_standard_clicked(self):
        dispense_vol = self.spinBox_standard.value()
        print(dispense_vol)
        self.std_pump.dispense(str(dispense_vol))
        logging.info('dispensed  '+str(dispense_vol) + ' uL of standard')

    def load_standard_clicked(self):
        load_vol = self.spinBox_standard.value()
        print(load_vol)
        self.std_pump.load(str(load_vol))
        logging.info('loaded  '+str(load_vol) + ' uL of standard')

    # completely empty
    def empty_standard_clicked(self):
        self.std_pump.empty()
        logging.info('emptied standard')

    # completely fill syringe
    def fill_standard_clicked(self):
        self.std_pump.fill()
        logging.info('filled standard')


    def dispense_thios_clicked(self):
        dispense_vol = self.spinBox_thios.value()
        print(dispense_vol)
        self.pump.dispense(str(dispense_vol))
        logging.info('dispensed  '+str(dispense_vol) + ' uL of thiosulfate')

    def load_thios_clicked(self):

        load_vol = self.spinBox_thios.value()
        print(load_vol)
        self.pump.load(str(load_vol))
        logging.info('loaded  '+str(load_vol) + ' uL of thiosulfate')




    def dispense_vol(self,vol):
        try:
            #print('dispensing ' + str(vol) + ' uL')
            self.pump.dispense(str(vol))
            logging.info('dispensed  '+str(vol) + ' uL')
        except Exception as ex:
            print(ex)
            QMessageBox.warning(self,'','dispense ' + str(vol) + ' failed', \
                                QMessageBox.Ok)
    def dispense_1uL(self):
        self.dispense_vol(1)
    def dispense_10uL(self):
        self.dispense_vol(10)
    def dispense_100uL(self):
        self.dispense_vol(100)
    def dispense_1000uL(self):
        self.dispense_vol(1000)
    def dispense_5000uL(self):
        self.dispense_vol(5000)
#    def dispense_custom(self):
#        vol = self.lcdNumber_customvol.value
#        self.dispense_vol(vol)
    def show_titration_result(self):
        comment, ok =  QInputDialog.getText(self, "Get text","Your name:", QLineEdit.Normal, "")
        if ok:
            return comment
        else:
            return None


def getPorts():
    ports = serial.tools.list_ports.comports()
    if not ports:
        return ("No Serial Port Detected",'This is not a port')
    else:
        return ports

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    prog = AppWindow()
    prog.show()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)
