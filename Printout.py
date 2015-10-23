#!/usr/bin/python3
#Print various

from Readvoltage import ADCTEMP
import time
import os

RTD = ADCTEMP()

while (True):
	#clear console
	os.system('clear')
	
	#Read and print
	print("Resistance: %.2f" % RTD.Resistance(1))
	print("Temperature: %.2f" % RTD.Temperature(1))
	
	time.sleep (5)
