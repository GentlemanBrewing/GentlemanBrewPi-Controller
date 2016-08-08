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
    self.processinformation = loadconfig()
    
  # Function for loading config file
  def loadconfig():
	  f = open('Config.yaml')
	  datamap = yaml.safe_load(f)
	  f.close
  return datamap
  
  # Function for updating config file
  def writeconfig(data):
  	f = open('Config.yaml', "w")
  	yaml.dump(data, f)
  f.close
  
  # Check processes to spawn
  def parse_config:
  	
  		
  
  # Write to database
  def database_write:
  	
  
  
  
  if __name__ == 'main':
  	# Create processes for each process in config file
  	for each process in self.processinformation.items():
		process['process_data']['object'] = Worker()
  		
  	
