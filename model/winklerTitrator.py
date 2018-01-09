#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  4 10:57:32 2018

@author: dnicholson
"""
from tinydb import TinyDB, Query
import numpy as np

class winklerTitrator:
    def __init__(self,meter,pump,datadir='./data',mode='normal',db=None):
        
        self.meter = meter
        self.pump = pump
        if not db:
            db = TinyDB('path/to/db.json')
        else:
            db = db
            
    def gran(uL,mV,T,vbot=125):
        # compute gran factor
        R = 8.314462175    #Ideal gas constant 
        F = 9.6485339924e4 #Faraday Constant Coulumbs mol-1
        TK0 = 273.15
        vbotL = 1e-3 * vbot
        vL = 1e-6 * uL
        EV = 1e-3 * mV
        TK = T + TK0
        a = R * TK / (2 * F)
        granVals = (vbotL + vL) * np.exp(EV / a)
        return granVals

    def gran2mV(uL,gF,T,vbot=125):
        # invert gran factor to get equivalent mV reading
        R = 8.314462175    #Ideal gas constant 
        F = 9.6485339924e4 #Faraday Constant Coulumbs mol-1
        TK0 = 273.15
        vbotL = 1e-3 * vbot
        vL = 1e-6 * uL
        #EV = 1e-3 * mV
        TK = T + TK0
        a = R * TK / (2 * F)
        mV = 1e3 * a * np.log(gF / (vbotL + vL))
        return mV