#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 21 13:06:49 2017

@author: dnicholson
"""
import os
import numpy as np
from gsw import density as dens
from time import strftime,gmtime,sleep
import json
import logging

class titration():
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
        self.DEBUG = False
        # when True the meter makes a reading (e.g. in DI water) but dummy_read
        # is called and mock data returned
        self.dummy_meter = True
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
        self.pump.setPos(0)

    def gran_fac(self):
        """
        calculates gran factor for titration
        """
        gran_factor = gran(self.uL,self.mV,self.T,vbot=self.vbot)
        self.gF = gran_factor
        return gran_factor

    def concentration(self,units='umolkg'):
        """
        calculates O2 concentration for a completed titration
        """
        # total moles of O2 in sample
        if self.is_complete:
            nO2 = (self.endpoint-self.Vblank)*self.Mthios / (4e6)
            cO2 = 1e12 * (nO2-self.reagO2) / ((1000 + \
                         dens.sigma0(self.S,self.Ts)) * \
                        (self.botvol-self.reagvol))
            return cO2

    def titrate(self,guess,vmax=3000):
        """
        Start and execute titration
            1. Titrate 10%, 20%, 30%, 40% of first guess
            2. estimate endpoint from linear fit to gran factor
            3. use 'target' to determine subsequent dispenses and iterate
            4. cleanup and save result
        """
        if not self.DEBUG:
            if not self.pump.is_open:
                logging.INFO('pump not connected')
            elif not self.meter.is_open:
                logging.warning('meter not connected')
            elif self.is_complete:
                logging.warning('sample already titrated')
        self.pump.setPos(0)
        sleep(0.1)
        ini_vol = 0.1*guess
        # titrate to 40% and predict endpoint
        for x in range(4):
            print('starting x= ' + str(x))
            if self.DEBUG:
                self.dispense_from_data(ini_vol)
            else:
                self.dispense(ini_vol)
            self.v_end_est = np.append(self.v_end_est,0)
            self.latest_line()
        self.gran_fac()

        fit = np.polyfit(self.gF[-4:],self.uL[-4:],1)
        # predicted endpoint with some safety bounds
        self.v_end = np.clip(fit[1],0,vmax)
        self.v_end_est[-1] = fit[1]
        logging.info('1st estimated endpoint: '+  str(fit[1]) + ' uL' )
        tgt_vol = self.target(self.v_end,self.mode)
        logging.info('target: ' + str(tgt_vol))
        while True:
            if self.DEBUG:
                self.dispense_from_data(tgt_vol)
            else:
                self.dispense(tgt_vol)
            fit = np.polyfit(self.gF[-4:],self.uL[-4:],1)
            logging.info('fit: ' + str(fit))
            self.v_end_est = np.append(self.v_end_est,fit[1])
            self.latest_line()
            logging.info('estimated endpoint: '+  str(fit[1]) + ' uL' )
            # predicted endpoint with some safety bounds
            if self.gF[-1] / self.gF[1] > 0.005:
                self.v_end = np.clip(fit[1],0,vmax)
            tgt_vol = self.target(self.v_end,mode=self.mode)
            logging.info('target is: ' + str(tgt_vol) + ', uL is ' + str(self.cumvol)\
                  + 'cumvol is: ' + str(self.cumvol))
            if not tgt_vol:
                break
        # cleanup and save when done
        self.endpoint = self.v_end
        to_endpoint_vol = self.endpoint - self.cumvol
        if to_endpoint_vol > 0:
            self.pump.movr(str(to_endpoint_vol))
            logging.info(str(to_endpoint_vol) + ' uL dispensed to reach endpoint')
        logging.warning('endpoint reached: ' + str(self.v_end) + ' uL')
        self.gran_fac()
        self.end_time = strftime("%Y%m%d%H%M%S", gmtime())
        self.is_complete = True
        #self.O2 = self.concentration()
        self.toJSON()
        self.pump.setPos(0)


    def dispense(self,vol):
        """
        dispense a given volume, then read meter and update fields
        """
        dispense_time = self.pump.wait_for_dispense(vol)
        print(str(dispense_time) + 'secs')
        self.pump.movr(str(vol))
        logging.info('dispensing ' + str(vol) + ' uL')
        sleep(dispense_time)
        sleep(0.5)
        logging.info('cumulative vol: ' + str(self.cumvol) + ' uL')
        sleep(0.5)
        print('reading meter...')
        mV,T = self.meter.meas()
        self.cumvol = self.pump.getPos()
        print(str(mV)+ ' T: '+str(T))
        if self.dummy_meter:
            T = 20
            mV = self.dummy_read(self.cumvol)
        #else:
            #mV,T = self.meter.meas()
        self.mV = np.append(self.mV,mV)
        self.T = np.append(self.T,T)
        self.uL = np.append(self.uL,self.cumvol)
        self.gran_fac()

    def dispense_from_data(self,vol):
        """
        virtual debug titration for when neither pump nor meter are connected
        """
        logging.info('dispense from data ' + str(vol) + ' uL')
        T = 20
        self.T = np.append(self.T,T)
        self.cumvol += vol
        self.uL = np.append(self.uL,self.cumvol)
        self.mV = np.append(self.mV,self.dummy_read(self.cumvol))
        self.gran_fac()
        sleep(1)

    def target(self,v_end,mode):
        """
        calculate how much to dispense in next step
        """
        if mode == 'rapid':
            #logging.info(v_end,self.cumvol)
            gran_tgt = v_end + np.array([-400,-200, -100,-60, -30, -10, -5, -3])
            gran_window = v_end + np.array([-450,-230, -120,-70, -35, -15, -8, -5])
            windowdiff = gran_window - self.cumvol

            tgtdiff = gran_tgt-self.cumvol
            logging.info('target ranges are: ' + str(tgtdiff))
            #logging.info(str(tgtdiff,windowdiff))
            # the first target that is at least 1 uL more than amount dispensed
            itgt = np.argmax(windowdiff > 1)

            if not itgt and windowdiff[0] <= 1:
                return False
            else:
                logging.info('gran target ' + str(gran_tgt[itgt]))
                logging.info('vol target ' + str(tgtdiff[itgt]))
                return np.round(tgtdiff[itgt])
        else:
            vol_to_end = v_end-self.cumvol;
            if vol_to_end > 300:
                return(150)
            elif vol_to_end > 100:
                return(50)
            elif vol_to_end > 40:
                return(20)
            elif vol_to_end > 20:
                return(10)
            elif vol_to_end > 8:
                return(5)
            elif vol_to_end > 5:
                return(3)
            elif vol_to_end > 1.5:
                return(1)
            elif vol_to_end > -1.5:
                return(0.5)
            elif vol_to_end > -5:
                return(1)
            elif vol_to_end > -20:
                return(5)
            elif vol_to_end > -30:
                return(10)
            elif vol_to_end <= -30:
                return False

    def toJSON(self):
        titr = {}
        attributes = ('botid','Mthios','vbot','Vblank','init_time','v_end',\
                      'end_time','endpoint','mode')
        npatts = ('mV','uL','T','v_end_est','endpoint')
        for att in attributes:
            titr[att] = getattr(self,att)
        for npatt in npatts:
            titr[npatt] = getattr(self,npatt).tolist()
        j = json.dumps(titr, default=lambda o: o.__dict__,
            sort_keys=True, indent=4)
        with open(os.path.join(self.datadir,'titration_'+\
                               strftime("%Y%m%d%H%M%S", gmtime())+'.json'),'w') as f:
            f.write(j)
        return j

    def save(self):
        import pickle
        fname = 'o2_' + self.end_time + '_' + self.botid
        pickle.dumps(self,open(fname,'wb'))
        return fname

    # parse titration object to write a line of text
    def latest_line(self):
        line_list = (strftime("%Y%m%d%H%M%S", gmtime()),str(self.uL[-1]), \
                str(self.mV[-1]),str(self.gF[-1]),str(self.T[-1]),\
                str(self.v_end_est[-1]))
        line = ','.join(line_list)+'\n'
        with open(self.current_file,'a') as f:
            f.write(line)
        return line

    def dummy_read(self,vol):
        # dummy titration data for debugging code w/o having to titrate...
        # below data is copied from output of a real titration
        uLp = np.array((80,160,240,320,470,520,570,620,670,720,740,760,780,790,800,803,\
              806,809,810,811,812,813,814,815,815.5,816,816.5,817.5,818.5,\
              819.5,820.5,821.5,822.5,827.5,837.5,847.5,857.5))
        mVp = np.array((391.6,389.8,387.9,385.8,380.5,378.7,376.3,373.3,369.8,364.8,\
              362.4,359.2,354.9,352.4,348.7,347.6,346.1,344.8,344.3,343.8,\
              343.2,342.5,342.1,341.2,340.8,340.4,340.2,339.1,338.1,337.0,\
              335.9,334.6,333.3,323.3,248.1,240.1,236.0))
        uLg = np.arange(0,1000)
        mVg = np.interp(uLg,uLp,mVp)
        mV_est = np.interp(vol,uLg,mVg)
        return(mV_est)

def gran(uL,mV,T,vbot=125):
    # compute gran factor
    R = 8.314462175    #Ideal gas constant
    F = 9.6485339924e4 #Faraday Constant Coulumbs mol-1
    TK0 = 273.15
    vbotL = 1e-3 * float(vbot)
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
