#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  2 20:19:42 2018

@author: dnicholson
"""

import csv
import logging

def import_flasks(fname):
    """
    Import flask calibration data from CSV file.
    First column should contain flask IDs (strings)
    Second column should contain flask volumes (floats)
    
    Args:
        fname (str): Path to CSV file containing flask calibrations
        
    Returns:
        dict: Dictionary mapping flask IDs to volumes
        
    Raises:
        ValueError: If file cannot be read or has incorrect format
    """
    try:        
        botvols = {}
        with open(fname, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row
            
            for row in reader:
                try:
                    if len(row) < 2 or not row[0] or not row[1]:  # Skip empty rows
                        continue
                        
                    # Convert ID to string, handling both string and number inputs
                    id_str = str(row[0]).strip()
                    
                    # Convert volume to float
                    vol_float = float(row[1])
                    
                    botvols[id_str] = vol_float
                    
                except (ValueError, TypeError, IndexError) as e:
                    logging.warning(f"Error processing row: {row}")
                    continue
        
        if not botvols:
            raise ValueError("No valid flask calibration data found")
            
        logging.info(f"Successfully loaded {len(botvols)} flask calibrations")
        return botvols
        
    except Exception as e:
        raise ValueError(f"Error processing flask calibration data: {str(e)}")
            
            
