#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 26 2020

@author: dnicholson
"""
import os
import numpy as np
from gsw import density as dens
from time import strftime,gmtime,sleep
import json
import logging

class standard():
    """
    Class representing a Winkler titration of a single sample (or std)
    """
    root_dir = os.path.join(os.path.expanduser('~'),'winkler-titrator')
    def __init__(self,meter,pump,botid,vbot,Mthios,datadir=os.path.join(root_dir,'data'),mode='normal'):
        """
        Initialize titration
        INPUTS:
         meter: meter object from serialDevices.py
         pump:  pump object from serialDevices.py
         botid: string id for iodine titration flask
         M_thios: Molarity of thiosulfate titrant
         datadir: directory path for saving output
         mode:    'normal' or 'rapid' (rapid stops before endpoint and
         traverses titration curve more quickly)
        """
        self.mode = mode
        self.meter = meter
        self.pump = pump
        self.botid = botid
        self.Mthios = Mthios
        self.cumvol = 0
        self.is_complete = False
        self.uL = np.array([])
        self.mV = np.array([])
        self.T = np.array([])
        self.v_end_est = np.array([])
        self.v_end = 0
        #self.pump.setPos(0)
        self.vbot = vbot
        # when True there are no actual pumping or meter reads
        self.DEBUG = True
        # when True the meter makes a reading (e.g. in DI water) but dummy_read
        # is called and mock data returned
        self.dummy_meter = False
        self.O2 = np.array([])
        self.Vblank = 0
        self.reagO2 = 7.6e-8; # concentration of O2 dissolved in reagents
        self.reagvol = 2;  # mL of reagent added
        self.init_time = strftime("%Y%m%d%H%M%S", gmtime())
        # Output is written to a temporary file which is accessed by the
        # plotting GUI
        self.current_file = os.path.join(datadir,'current.csv')
        self.datadir = datadir
        if not os.path.exists(datadir):
            os.makedirs(datadir)
        with open(self.current_file,'w') as self.f:
            self.f.write('time,uL,mV,gF,temp,v_end_est\n')
