#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 22 10:08:26 2017

@author: dnicholson
"""

import serialDevices as sd
import titration as ti

#orion = sd.meter('/dev/tty.usbserial-FTXV1D01A')
orion = sd.meter('/dev/tty.lpss-serial1')
#mg = sd.pump('/dev/tty.usbserial-FTXV1D01C')
mg = sd.pump('/dev/tty.lpss-serial1')
tt = ti.titration(orion,mg,'A22',125,0.2000,mode='rapid')
tt.titrate(1000)