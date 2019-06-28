#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 20 15:09:00 2017

@author: dnicholson
"""

#CHANGES TRACKED WITH:
###########################################################################
# RI

import serial
import time

class meter(serial.Serial):
    """
    Serial device object for Thermo Orion Meter
    Be sure meter probe and serial cables are connected
    """

    def readline(self,eol=b'\n\r'): ###########################################
    #def readline(self,eol='\r'):
        """
        read line of output -  meter uses '\r' terminator. replaces
        Serial.serial.readline() which only works with '\n'
        returns bytes
        """
        #eol = b'\r'
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
        if self.in_waiting:
            self.reset_input_buffer()
        self.write(b'GETMEAS\r')
        # wait for echo
        time.sleep(0.2)
        try:
            if self.in_waiting:
                # first line is echo of command
                bline = self.readline()
                time.sleep(0.1)
            if self.in_waiting:
                bline = self.readline()
                print(bline)
                line = str(bline)
                meas_list = line.split(',')
                if meas_list:
                    mV = float(meas_list[10])
                    T = float(meas_list[12])
                return (mV,T)
        except:
             print('no response')

class pump(serial.Serial):
    def __init__():
        super().__init__()
    TERMINATOR = '\r\n'
    # redefine readline to work for \r line termination
    def readline(self,eol=TERMINATOR.encode('utf-8')):
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
            else:
                break
        return bytes(line[:-leneol])

    def setVar(self,var,val,eol=TERMINATOR):
        valstr = str(val)
        self.write((var + '=' + valstr + eol).encode('utf-8'))

class mforce_pump(serial.Serial):
    """
    original controller uLynx
    Serial device object for milligat LF pump with MFORCE controller
    Be sure pump is powered and serial cable connected
    since this is a 422 device, it requires an address which precedes each comman
    default is A
    """
    TERMINATOR = '\r\n'
    def __init__():
        print('hello')
        super().__init__()
        self.setPos(self,0)
        self.address='A'
        self.MUNIT=23104

    def setVar(self,var,val,eol=TERMINATOR):
        valstr = str(val)
        self.write(self.addr + (var + '=' + valstr + eol).encode('utf-8'))

    def getVar(self,var,eol=TERMINATOR):
        self.reset_input_buffer()
        #bmsg = ('PR ' + var.lower() + eol).encode('utf-8')
        bmsg = (self.addr + 'PR ' + var.lower() + eol).encode('utf-8')
        print(var.lower)
        print(var.lower())
        self.write(bmsg)
        time.sleep(.5)
        if self.in_waiting:
            bline = self.readline()
            # if command is echoed, read next line
            print(bline)
            print(bmsg)
            #time.sleep(.1)
            #if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
            bline = self.readline()
            print(bline)
            val = float(bline)
            return val
        else:
            print('no response -- check connnection')

    def setPos(self,val,eol=TERMINATOR):
        valstr = str(val)
        self.write((self.addr + 'P = ' + valstr + eol).encode('utf-8'))

    def getPos(self,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = (self.addr + 'PR P' + eol).encode('utf-8')
        self.write(bmsg)
        time.sleep(0.2)
        if self.in_waiting:
            bline = self.readline()
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
            pos = float(bline)/self.MUNIT
            return pos
        else:
            print('no response -- check connnection')


    def movr(self,uL,eol=TERMINATOR):
        # dispense - relative pump movement
        # 1 ul = 23104 steps
        steps = int(float(uL))*self.MUNIT
        print (self.addr + 'MR ' + str(steps))
        self.write((self.addr + 'MR ' + str(steps) + eol).encode('utf-8'))


    def mova(self,uL,eol=TERMINATOR):
        # dispense - move pump to absolute position
        steps = int(float(uL))*self.MUNIT
        print (self.addr + 'MA ' + str(steps))
        self.write((self.addr + 'MA ' + str(steps) + eol).encode('utf-8'))

    def setVM(self,uL,eol=TERMINATOR):
        # dispense - set rate
        steps = int(float(uL))*self.MUNIT
        print('VM ' + str(steps))
        self.write((self.addr + 'VM ' + str(steps) + eol).encode('utf-8'))

    def wait_for_dispense(self,uL,eol=TERMINATOR):
        #uLynx
        #called from titration.py
        # maximum rate in uL sec-1
        #self.write(('MR ' + str(uL*self.MUNIT4) + eol).encode('utf-8'))
        max_rate = self.getVar('VM') # steps per second
        steps = int(float(uL))*self.MUNIT
        #max_rate = steps
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = steps / max_rate + 0.2
        print('wait time ' + str(wait_time))
        return wait_time

class mlynx_pump(pump):
    """
    Serial device object for milligat LF pump with microlynx controller
    Be sure pump is powered and serial cable connected
    """
    TERMINATOR = '\r\n'
    # redefine readline to work for \r line termination
    def getVar(self,var,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = ('print ' + var.lower() + eol).encode('utf-8')
        self.write(bmsg)
        time.sleep(0.2)
        if self.in_waiting:
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
            print(bline)
            val = float(bline)
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
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
            pos = float(bline)
            return pos
        else:
            print('no response -- check connnection')


    def movr(self,uL,eol=TERMINATOR):
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
