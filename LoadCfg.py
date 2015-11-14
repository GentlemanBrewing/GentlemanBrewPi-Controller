#!/usr/bin/python3
#Load CFG file data

import yaml
import os
import time

def Loadconfig():
	f = open('Config.yaml')
	dataMap = yaml.safe_load(f)
	f.close()
	return dataMap

def Writeconfig(data):
	f = open('Config.yaml', "w")
	yaml.dump(data, f)
	f.close	


Config = Loadconfig()
print(Config)
datanew = {'Kp' : 5000, 'Ki' : 300, 'Kd' : 0, 'Setpoint' : 18}
Writeconfig(datanew)
