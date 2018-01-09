#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 20 15:09:00 2017

@author: dnicholson
"""

import serial
import time

class meter(serial.Serial):
    """
    Serial device object for Thermo Orion Meter
    Be sure meter probe and serial cables are connected
    """       

    def readline(self,eol=b'\r'):
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
                    break
            else:
                break
        return bytes(line[:-leneol])

    # send command to make measurement and return parsed output
    def meas(self):
        """
        makes single meter measurement for mV and T
        """
        if self.in_waiting:
            self.flush()
        self.write(b'GETMEAS\r')
        # wait for echo
        time.sleep(0.2)
        try:
            if self.in_waiting:
                # first line is echo of command
                line = self.readline()
                print(line)
                line = str(self.readline())
                print(line)
                meas_list = line.split(',')
                if meas_list:
                    mV = float(meas_list[5])
                    T = float(meas_list[7])
                return (mV,T)
        except:
             print('no response')
             
        
class pump(serial.Serial):
    """
    Serial device object for milligat LF pump with microlynx controller
    Be sure pump is powered and serial cable connected
    """  
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
        
        

