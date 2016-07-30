#!/usr/bin/python3

import datetime
import os
import time
import yaml
import RPi.GPIO as GPIO
from Readvoltage import ADCTEMP


adc = ADCTEMP()

# function for loading config file
def Loadconfig():
	f = open('Config.yaml')
	dataMap = yaml.safe_load(f)
	f.close
	return dataMap

# function for updating config file
def Writeconfig(data):
	f = open('Config.yaml', "w")
	yaml.dump(data, f)
	f.close


variables = Loadconfig()
Setpoint = variables['Setpoint']
	
Relay_Output = 0
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)
while (True):
	temperature = adc.Temperature(1)
	if temperature > 10 :
		GPIO.output(27, True)
	#elif temperature < Setpoint -1:
		#GPIO.output(27, False)
	
	print(temperature)
	time.sleep(5)
