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
    def __init__(self,port,mVpos,Tpos):
        self.mVpos = mVpos
        self.Tpos = Tpos
        super().__init__(port)

    def readline(self,eol=b'\n\r'): #need to change to \n\r for AXXX meters?
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
        time.sleep(0.2)
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
        try:
            mV = float(meas_list[self.mVpos])
            T = float(meas_list[self.Tpos])
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

    print('hello')
    addr='A'
    MUNIT=2432
    TERMINATOR = '\r\n'

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

    def setVar(self,var,val,eol=TERMINATOR):
            valstr = str(val)
            self.write((self.addr + var + ' ' + valstr + eol).encode('utf-8'))

    def setPos(self,val,eol=TERMINATOR):
        valstr = str(val)
        self.write((self.addr + 'P ' + valstr + eol).encode('utf-8'))

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
        self.write((s.self.addr + 'VM ' + str(steps) + eol).encode('utf-8'))

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
        self.write(bmsg)
        time.sleep(0.2)
        if self.in_waiting:
            bline = self.readline()
            bline = self.readline()
            # if command is echoed, read next line
            if bline[len(eol)-len(bmsg):] == bmsg[:-len(eol)]:
                bline = self.readline()
                print('second ' + bline)
            val = float(bline)
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
            bline = self.readline()
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

"""
Kloehn V6 pump
"""

class kloehn_pump(serial.Serial):
    """
    Serial device object kloehn v6 syringe pump
    Be sure pump is powered and serial cable connected
    """
    TERMINATOR = '\r\n'
    def __init__(self,port,steps=48000,syringe_vol=1000,VM='500',InAddr='1',OutAddr='2'):

        eol = '\r\n'
        self.SF = float(steps)/float(syringe_vol)
        self.VM = VM
        self.syringe_vol = syringe_vol
        self.steps = steps
        self.InPos = ('/o' + InAddr + 'R' + eol).encode('utf-8');
        self.InOut = ('/o' + OutAddr + 'R' + eol).encode('utf-8');
        super().__init__(port)
        #intitialize command required on power-up
        self.write(('/1W4R'+ eol).encode('utf-8'))
        #set max velocity (steps/sec)
        bmsg = ('/1V'+str(VM)+'R'+ eol).encode('utf-8')
        print(bmsg)
        self.write(bmsg)
        #logging.INFO('wrote ' +  str(bmsg))
        print('connecting kloehn pump'+ ' VM msg is ' + str(bmsg))
        #logging.INFO('connecting kloehn pump')
        #bmsg = ('/1' + 'V' + self.VM + 'R' + eol).encode('utf-8')



    # redefine readline to work for \r line termination
    # def isBusy(self,var,eol=TERMINATOR):
        # self.reset_input_buffer()
        # bmsg = ('/1' + eol).encode('utf-8')
        # self.write(bmsg)
        # bline = self.readline()
        # if string(bline) = '@':
            # return True
        # elseif string(bline).st
            # return False
    def setPos(self,pos=0,eol=TERMINATOR):
        self.write(self.InPos)
        time.sleep(1)
        ### FIX THIS
        self.mova(self.syringe_vol)

    def getPos(self,eol=TERMINATOR):
        b =self.read(self.in_waiting)
        while self.in_waiting < 10:
            self.write('/1?\r'.encode('utf-8'))
            time.sleep(0.1)
        b =self.read(self.in_waiting)
        print(b)
        l = str(b).split("`")
        l2 = l[1].split("\\")
        posstr = str(l2[0])
        print(posstr)
        pos = int(posstr)
        return (float(self.steps)-pos)/self.SF


    # funtion to pass any command to pump (not tested)
    def sendCommand(self,msg,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = (msg.lower() + eol).encode('utf-8')
        self.write(bmsg)
        time.sleep(0.2)
        if self.in_waiting:
            bline = self.readline()
            print(bline)
            return bline

        else:
            print('no response -- check connnection')


    def getValvePos(self,eol=TERMINATOR):
        self.reset_input_buffer()
        bmsg = ('?8' + eol).encode('utf-8')
        return str(bmsg)

    # move relative amount
    def movr(self,uL,eol=TERMINATOR):
        # dispense - relative pump movement
        val = float(uL)
        if val >= 0:
            self.dispense(uL)
        else:
            self.load(uL)


    # move absolute amount
    def mova(self,uL,eol=TERMINATOR):
        # dispense - move pump to absolute position
        val = float(uL)
        step = round(val*self.SF)
        stepstr = str(step)
        print(stepstr)
        self.write(('/1A' + stepstr + 'R' + eol).encode('utf-8'))

    def dispense(self,uL,eol=TERMINATOR):
        stepstr = str(int(float(uL)*self.SF+0.5))
        print('step: '+ stepstr)
        self.write(self.OutPos);
        time.sleep(0.5)
        self.write(('/1D' + stepstr + 'R' + eol).encode('utf-8'))
        time.sleep(self.wait_for_dispense(uL))

    def load(self,uL,eol=TERMINATOR):
        stepstr = str(int(float(uL)*self.SF+0.5))
        print('step: '+ stepstr)
        self.write(self.InPos);
        time.sleep(0.5)
        self.write(('/1P' + stepstr + 'R' + eol).encode('utf-8'))
        time.sleep(self.wait_for_dispense(uL))

    def fill(self,eol=TERMINATOR):
        print('fillling' + str(self.steps))
        self.write(self.InPos);
        time.sleep(1.0)
        self.write(('/1A' + str(self.steps) + 'R' + eol).encode('utf-8'))
        #time.sleep(self.wait_for_dispense(uL))

    def empty(self,eol=TERMINATOR):
        self.write(self.OutPos);
        time.sleep(0.5)
        self.write(('/1A0R' + eol).encode('utf-8'))

    def wait_for_dispense(self,uL):
        # maximum rate in uL sec-1
        uL = float(uL)
        max_rate = float(self.VM)/self.SF
        # wait for dispense to complete (add 0.2 secs for accel/decel)
        wait_time = abs(uL) / float(max_rate) + 0.2
        return wait_time
