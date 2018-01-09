#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 20:19:42 2018

@author: dnicholson
"""

import pandas as pd

def import_flasks(fname):
    try:
        df = pd.read_excel('./model/winklerbottlecal.xlsx',usecols=(0,1),\
                           dtype=('str','float'))
        botvols = dict(zip(df.botid,df.vol))
        return botvols
    except:
        return None