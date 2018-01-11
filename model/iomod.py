#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 20:19:42 2018

@author: dnicholson
"""

import xlrd

def import_flasks(fname):
    try:        
        book = xlrd.open_workbook(fname)
        sheet  = book.sheet_by_index(0)
        botid = sheet.col_values(0,1)
        botstr = [str(i) for i in botid]
        vol = sheet.col_values(1,1)
        botvols = dict(zip(botstr,vol))
    except:
        botvols = None
    return botvols
            
            
