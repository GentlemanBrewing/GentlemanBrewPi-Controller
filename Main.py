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
Setpoint = variables['Steam Boiler']['setpoint']
	
Relay_Output = 0
GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)
#while (True):
temperature = adc.Temperature(1)
	#if temperature > Setpoint +1:
GPIO.output(22, True)
	#elif temperature < Setpoint -1:
		#GPIO.output(22, False)
	
print(temperature)
print(Setpoint)
time.sleep(5)
GPIO.cleanup()
