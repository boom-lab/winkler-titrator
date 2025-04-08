#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 20:19:42 2018
Updated on Apr 8 2024 to use CSV instead of Excel

@author: dnicholson
"""

import csv

def import_flasks(fname):
    """Import flask calibration data from CSV file.
    
    Parameters
    ----------
    fname : str
        Path to CSV file containing flask calibration data.
        Expected format: two columns, first column is bottle ID, second is volume.
        First row should be header.
    
    Returns
    -------
    dict
        Dictionary mapping bottle IDs (as strings) to volumes
    """
    try:
        with open(fname, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            botvols = {}
            for row in reader:
                if len(row) >= 2:  # Ensure row has at least 2 columns
                    botid = row[0].strip()  # Keep ID as string, just strip whitespace
                    try:
                        vol = float(row[1])  # Convert volume to float
                        botvols[botid] = vol
                    except ValueError:
                        print(f"Warning: Could not convert volume '{row[1]}' to float for bottle {botid}")
                        
    except Exception as e:
        print(f"Error reading flask calibration file: {e}")
        botvols = None
        
    return botvols
            
            
