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

    def readline(self,eol=b'\r'): ###########################################
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
            self.flush()
        self.write(b'GETMEAS\r') #add \n here???
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
                    mV = float(meas_list[10])
                    T = float(meas_list[12])
                return (mV,T)
        except:
             print('no response')
             
        
class pump(serial.Serial):
    """
    original controller uLynx
    Serial device object for milligat LF pump with MFORCE controller
    Be sure pump is powered and serial cable connected
    since this is a 422 device, it requires an address which precedes each comman
    default is A
    """
    #TERMINATOR = '\r\n'
    TERMINATOR = '\r\n' ##########################################################################
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
        #bmsg = ('PR ' + var.lower() + eol).encode('utf-8')
        bmsg = ('PR n ' + var.lower() + eol).encode('utf-8')
        print(var.lower)
        print(var.lower())
        self.write(bmsg)
        time.sleep(.5)
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
        self.write(('P =' + valstr + eol).encode('utf-8'))
        
    def getPos(self,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = ('PR P' + eol).encode('utf-8')
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
        # 1 ul = 23104 steps
        steps = int(uL)*23104
        print ('MR ' + str(steps))
        self.write(('MR ' + str(steps) + eol).encode('utf-8'))

               
    def mova(self,uL,eol=TERMINATOR):
        # dispense - move pump to absolute position
        steps = int(uL)*23104
        print ('MA ' + str(steps))
        self.write(('MA ' + str(steps) + eol).encode('utf-8'))
    
    def setVM(self,uL,eol=TERMINATOR):
        # dispense - set rate
        steps = int(uL)*23104
        print('VM ' + str(steps))
        self.write(('VM ' + str(steps) + eol).encode('utf-8'))

    def wait_for_dispense(self,uL,eol=TERMINATOR):
        #uLynx
        #called from titration.py
        # maximum rate in uL sec-1
        #self.write(('MR ' + str(uL*23104) + eol).encode('utf-8'))
        max_rate = self.getVar('VM') # steps per second
        steps = int(uL)*23104
        #max_rate = steps
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = steps / max_rate + 0.2
        print('wait time ' + str(wait_time))
        return wait_time
        
        
