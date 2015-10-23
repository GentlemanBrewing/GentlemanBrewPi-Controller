#!/usr/bin/python3
# Log voltage as read from adc


from Readvoltage import ADCTEMP
import datetime
import time
import os

adc = ADCTEMP()

#function for writing to file
def writetofile(texttowrite):
	f = open('Templog.txt', 'a')
	f.write(str(datetime.datetime.now()) + " " + texttowrite + "\n")
	f.closed


while (True):
	#Read temperature from the adc
	writetofile("Temperature: %.2f " % adc.Temperature(1))
	
	#Wait 5 seconds between measurements
	time.sleep(5)
