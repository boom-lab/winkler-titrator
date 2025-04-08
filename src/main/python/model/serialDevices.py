#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 20 15:09:00 2017

@author: dnicholson
"""

import serial
import time
import configparser
import logging
import os

root_dir = os.path.join(os.path.expanduser('~'),'winkler-titrator')
config = configparser.ConfigParser()
config.read(os.path.join(root_dir,'wink.ini'))

class meter(serial.Serial):
    """
    Serial device object for Thermo Orion Meter
    Be sure meter probe and serial cables are connected
    """
    def __init__(self, port, mVpos=5, Tpos=7, type='thermo', debug=False):
        self.mVpos = mVpos
        self.Tpos = Tpos
        self.type = type
        self.DEBUG = debug  # Store debug flag
        self._debug_potential = 0.0
        self._debug_temperature = 25.0
        
        if not debug:
            super().__init__(port, timeout=10)
            if type=='atlas':
                self.write(b'*OK,0\r')
                self.write(b'C,0\r')
                time.sleep(0.2)
                b = self.read(self.in_waiting)
                print(b.decode())

    #def readline(self,eol=b'\n\r'): #need to change to \n\r for AXXX meters?
    def readline(self,eol='\r'):
        """
        read line of output -  meter uses '\r' terminator. replaces
        Serial.serial.readline() which only works with '\n'
        returns bytes
        """
        eol = bytes(eol)
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    return bytes(line[:-leneol])
            else:
                break
        return bytes(line[:-leneol])

    # send command to make measurement and return parsed output
    def meas(self):
        """
        makes single meter measurement for mV and T
        """
        time.sleep(0.2)
        if self.type == "thermo":
            self.write(b'\r')
            self.read(self.in_waiting)
            #self.reset_output_buffer()
            #self.reset_input_buffer()
            time.sleep(0.5)
            nin = self.write(b'GETMEAS\r')
            time.sleep(0.3)
            nw = self.in_waiting
            while nw <= 40:
                time.sleep(1)
                nw = self.in_waiting
            time.sleep(0.5)
            b = self.read(self.in_waiting)
            print(b)
            meas_list = b.decode().split(',')
            print(meas_list)
            try:
                mV = float(meas_list[self.mVpos])
                T = float(meas_list[self.Tpos])
                return (mV,T)
            except:
                print('read failed')
        # single read implemented here - no checks for stability
        elif self.type == "atlas":
            print("I'm an Atlas meter")
            self.write(b'R\r')
            time.sleep(0.2)
            b = self.readline()
            try:
                mV = float(b)
                T = -9
                return (mV,T)
            except:
                print('read failed')



class mforce_pump(serial.Serial):
    """
    original controller uLynx
    Serial device object for milligat LF pump with MFORCE controller
    Be sure pump is powered and serial cable connected
    since this is a 422 device, it requires an address which precedes each comman
    default is A
    """
    addr='A'
    MUNIT=2432
    TERMINATOR = '\r\n'

    def __init__(self, port, debug=False):
        self.DEBUG = debug
        self._debug_position = 0.0
        self._debug_volume = 0.0
        self._connection_status = False
        
        if not debug:
            super().__init__(port, timeout=10)
            self.reset_input_buffer()
            self.write(b'print pos' + self.TERMINATOR.encode('utf-8'))
            time.sleep(0.2)
            if self.in_waiting:
                bline = self.readline()
                try:
                    self._debug_position = float(bline)
                    self._connection_status = True
                except:
                    logging.error(f"Failed to parse initial position: {bline}")
                    self._connection_status = False

    @property
    def is_open(self):
        """Check if the serial port is open"""
        if self.DEBUG:
            return True
        return super().is_open

    @property
    def connection_status(self):
        """Check if the pump is connected and responding"""
        if self.DEBUG:
            return True
        if not self.is_open:
            return False
        try:
            # Try to get position to verify connection
            self.reset_input_buffer()
            msg = f"{self.addr}PR P{self.TERMINATOR}"
            self.write(msg.encode('utf-8'))
            time.sleep(0.2)
            if self.in_waiting:
                bline = self.readline()
                bline = self.readline()
                float(bline)  # Try to parse response
                return True
            return False
        except:
            return False

    def getVar(self, var, eol=TERMINATOR):
        if self.DEBUG:
            if var.lower() == 'pos':
                return self._debug_position
            return 0.0
            
        self.reset_input_buffer()
        msg = f"{self.addr}PR {var.lower()}{eol}"
        self.write(msg.encode('utf-8'))
        time.sleep(.5)
        if self.in_waiting:
            bline = self.readline()
            bline = self.readline()
            print(bline)
            val = float(bline)
            return val
        else:
            logging.error("No response from pump")
            return None

    def setPos(self, val, eol=TERMINATOR):
        if self.DEBUG:
            self._debug_position = val
            return
            
        msg = f"{self.addr}P {val}{eol}"
        self.write(msg.encode('utf-8'))

    def getPos(self, eol=TERMINATOR):
        if self.DEBUG:
            return self._debug_position
            
        self.reset_input_buffer()
        msg = f"{self.addr}PR P{eol}"
        self.write(msg.encode('utf-8'))
        time.sleep(0.2)
        if self.in_waiting:
            bline = self.readline()
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(msg.encode('utf-8')):] == msg.encode('utf-8')[:-len(eol)]:
                bline = self.readline()
            pos = float(bline)/self.MUNIT
            return pos
        else:
            logging.error("No response from pump")
            return None

    def fill(self, eol=TERMINATOR):
        if self.DEBUG:
            self._debug_position = 0.0
            self._debug_volume = 0.0
            return
            
        logging.warning('milligat pump - no fill')

    def dispense(self, uL, eol=TERMINATOR):
        if self.DEBUG:
            # Simulate dispensing
            volume = float(uL)
            self._debug_position += volume
            self._debug_volume += volume
            time.sleep(0.1)  # Simulate some delay
            return
            
        # dispense - relative pump movement
        steps = int(float(uL))*self.MUNIT
        msg = f"{self.addr}MR {steps}{eol}"
        self.write(msg.encode('utf-8'))

    def mova(self, uL, eol=TERMINATOR):
        # dispense - move pump to absolute position
        steps = int(float(uL))*self.MUNIT
        msg = f"{self.addr}MA {steps}{eol}"
        print(msg)
        self.write(msg.encode('utf-8'))

    def setVM(self, uL, eol=TERMINATOR):
        # dispense - set rate
        steps = int(float(uL))*self.MUNIT
        msg = f"{self.addr}VM {steps}{eol}"
        print(msg)
        self.write(msg.encode('utf-8'))

    def wait_for_dispense(self,uL,eol=TERMINATOR):
        #uLynx
        #called from titration.py
        # maximum rate in uL sec-1
        #self.write(('MR ' + str(uL*MUNIT4) + eol).encode('utf-8'))
        max_rate = self.getVar('VM') # steps per second
        steps = int(float(uL))*self.MUNIT
        #max_rate = steps
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = steps / max_rate + 0.2
        print('wait time ' + str(wait_time))
        return wait_time


    def fill(self,eol=TERMINATOR):
        print('milligat pump - no fill')

class mlynx_pump(serial.Serial):
    """
    Serial device object for milligat LF pump with microlynx controller
    Be sure pump is powered and serial cable connected
    """
    TERMINATOR = '\r\n'
    # redefine readline to work for \r line termination
    def getVar(self,var,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = ('print ' + var.lower() + eol).encode('utf-8')
        print(bmsg)
        self.write(bmsg)
        time.sleep(0.5)
        if self.in_waiting:
            bline = self.readline()
            print(bline)
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
                print('second ' + bline)
            val = float(bline[:-len(eol)])
            print(bline)
            return val
        else:
            print('no response -- check connnection')

    def setPos(self,val,eol=TERMINATOR):
        valstr = str(val)
        self.write(('pos =' + valstr + eol).encode('utf-8'))

    def getPos(self,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = ('print pos' + eol).encode('utf-8')
        self.write(bmsg)
        time.sleep(0.2)
        if self.in_waiting:
            #bline = self.readline()
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
            pos = float(bline)
            return pos
        else:
            print('no response -- check connnection')

    def fill(self,eol=TERMINATOR):
        print('milligat pump - no fill')

    def dispense(self,uL,eol=TERMINATOR):
        # dispense - relative pump movement
        self.write(('movr ' + uL + eol).encode('utf-8'))

    def mova(self,uL,eol=TERMINATOR):
        # dispense - move pump to absolute position
        self.write(('mova ' + uL + eol).encode('utf-8'))

    def wait_for_dispense(self,uL,eol=TERMINATOR):
        # maximum rate in uL sec-1
        max_rate = self.getVar('VM')
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = uL / float(max_rate) + 0.2
        return wait_time

"""
Kloehn V6 pump
"""

class kloehn_pump(serial.Serial):
    """
    Serial device object kloehn v6 syringe pump
    Be sure pump is powered and serial cable connected
    """
    TERMINATOR = '\r\n'
    
    def __init__(self, port, steps=48000, syringe_vol=1000, VM='500', InAddr='1', OutAddr='2', PumpAddr='/1', debug=False):
        self.DEBUG = debug
        self._debug_position = 0.0
        self._debug_volume = 0.0
        self.SF = float(steps)/float(syringe_vol)
        self.VM = VM
        self.syringe_vol = syringe_vol
        self.steps = steps
        self.pump_addr = PumpAddr
        self.InPos = (PumpAddr + 'o' + InAddr + 'R' + self.TERMINATOR).encode('utf-8')
        self.OutPos = (PumpAddr + 'o' + OutAddr + 'R' + self.TERMINATOR).encode('utf-8')
        
        if not debug:
            super().__init__(port, timeout=10)
            # Initialize pump
            self.write(('/1~Y' + OutAddr + 'R' + self.TERMINATOR).encode('utf-8'))
            time.sleep(0.1)
            self.write(('/1Y4R'+ self.TERMINATOR).encode('utf-8'))
            time.sleep(self.wait_for_dispense(float(self.steps)/float(self.VM)+0.2))
            # Set max velocity
            bmsg = (PumpAddr + 'V'+str(VM)+'R'+ self.TERMINATOR).encode('utf-8')
            self.write(bmsg)

    def getPos(self, eol=TERMINATOR):
        if self.DEBUG:
            return self._debug_position
            
        self.read(self.in_waiting)
        self.write((self.pump_addr + '?' + eol).encode('utf-8'))
        time.sleep(0.1)
        b = self.read(self.in_waiting)
        l = str(b).split("`")
        l2 = l[1].split("\\")
        posstr = str(l2[0])
        pos = int(posstr)
        return (float(self.steps)-pos)/self.SF

    def dispense(self, uL, eol=TERMINATOR):
        if self.DEBUG:
            # Simulate dispensing
            volume = float(uL)
            self._debug_position += volume
            self._debug_volume += volume
            time.sleep(0.1)  # Simulate some delay
            return
            
        stepstr = str(int(float(uL)*self.SF+0.5))
        self.write(self.OutPos)
        time.sleep(0.5)
        self.write(self.OutPos)
        time.sleep(1)
        self.write((self.pump_addr +'D' + stepstr + 'R' + eol).encode('utf-8'))
        time.sleep(self.wait_for_dispense(uL))

    def fill(self, eol=TERMINATOR):
        if self.DEBUG:
            self._debug_position = 0.0
            self._debug_volume = 0.0
            return
            
        self.write(self.InPos)
        time.sleep(1.0)
        try:
            cvol = self.getPos()
        except:
            cvol = self.syringe_vol
        self.write((self.pump_addr + 'A' + str(self.steps) + 'R' + eol).encode('utf-8'))
        time.sleep(float(cvol)*float(self.SF)/float(self.VM))

    def wait_for_dispense(self, uL):
        """
        calculates how long it will take for syringe to dispense a given volume
        """
        if self.DEBUG:
            return 0.1  # Simulate a short delay
            
        # maximum rate in uL sec-1
        uL = float(uL)
        max_rate = float(self.VM)/self.SF
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = abs(uL) / float(max_rate) + 0.2
        return wait_time
