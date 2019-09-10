#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: dnicholson
"""
# should be 'MLYNX' or 'MFORCE'
PUMP_CTRL = 'MLYNX'
# 'ORION' for blue old meters
# 'AXXX' for black newer meters
METER = 'ORION'

if METER == 'ORION':
    mVpos = 5
    Tpos = 7
elif METER == 'AXXX':
    mVpos = 8
    Tpos = 10
