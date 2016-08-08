#!/usr/bin/python3

import multiprocessing
import datetime
import time
from ABE_ADCPi import ADCPi
import RPi.GPIO as GPIO
import sqlite3

# Main Manager class
class brewmanager(multiprocessing.process):
  
  def __init__(self, inputqueue, outputqueue):
    multiprocessing.Process.__init__(self)
    
  # Function for loading config file
  def Loadconfig():
	  f = open('Config.yaml')
	  dataMap = yaml.safe_load(f)
	  f.close
  return dataMap
  
  # Function for updating config file
  def Writeconfig(data):
  	f = open('Config.yaml', "w")
  	yaml.dump(data, f)
  f.close
  
  
    
