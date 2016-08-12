#!/usr/bin/python3

import multiprocessing
import datetime
import time
from ABE_ADCPi import ADCPi
import RPi.GPIO as GPIO
import sqlite3
import yaml
import Controller
import os


# Buzzer class
class Buzzer(multiprocessing.Process):
    def __init__(self, inputqueue):
        multiprocessing.Process.__init__(self)
        self.inputqueue = inputqueue

        self.variabledict = {
            'frequency': 2000,
            'duty': 50,
            'duration': 1,
            'pin': 12,
            'terminate': 1
        }

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.variabledict['pin'], GPIO.OUT)

    def run(self):
        while True:
            # Check for new input
            try:
                updated_variables = self.inputqueue._nowait()
                for variable, value in updated_variables.items():
                    self.variabledict[variable] = value
            except Queue.Empty

            if self.variabledict['duration'] != 0:
                p = GPIO.PWM(self.variabledict['pin'], self.variabledict['frequency'])
                p.start(self.variabledict['duty'])
                time.sleep(self.variabledict['duration'])
                p.stop()
                self.variabledict['duration'] = 0
                GPIO.cleanup()

            time.sleep(1)




# Main Manager class
class BrewManager(multiprocessing.Process):

    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.processinformation = self.loadconfig('Config.yaml')
        self.conn = sqlite3.connect('Log.db')
        self.cur = self.conn.cursor()
        self.counter = 0
        self.processdata = {}

    # Function for loading config file
    def loadconfig(self, filename):
        f = open(filename)
        datamap = yaml.safe_load(f)
        f.close()
        return datamap
  
    # Function for updating config file
    def writeconfig(self, data):
        f = open('Config.yaml', "w")
        yaml.dump(data, f)
        f.close()

    def buzzer(self, frequency, duration):
        buzzervariables = {
            'frequency': frequency,
            'duration': duration
        }
        self.processdata['Buzzer']['inputqueue'].put(buzzervariables)

    # Function for writing to database
    def write_to_database(self):
        try:
            with self.conn:
                self.conn.execute('INSERT INTO PIDOutput(DateTime, ProcessName, Temperature, Duty, Setpoint, SafetyTemp, SafetyTrigger) VALUES (:DateTime, :ProcessName,'
                                  ':Temperature, :Duty, :Setpoint, :SafetyTemp, :SafetyTrigger)', self.data)
        except sqlite3.IntegrityError:
            self.buzzer(2000, 1)

    def run(self):
        # Initialize processes as per config file
        for process, pvariables in self.processinformation.items():
            if pvariables['terminate'] == 0:
                self.processdata[process]['inputqueue'] = multiprocessing.Queue()
                self.processdata[process]['outputqueue'] = multiprocessing.Queue()
                Controller.PIDController(self.processdata[process]['inputqueue'], self.processdata[process]['outputqueue']).start()
                self.processdata[process]['inputqueue'].put(pvariables)

        # Create buzzer process
        self.processdata['Buzzer']['inputqueue'] = multiprocessing.Queue()
        Buzzer(self.processdata['Buzzer']['inputqueue']).start()
        self.processdata['Buzzer']['inputqueue'].put(self.processinformation['Buzzer'])

        # Main loop
        while True:

            # Get output from process and record in database
            for process in self.processdata.keys():
                try:
                    self.data = self.processdata[process]['outputqueue'].get_nowait()
                    # Check for Safetytrigger from process and sound buzzer if present
                    if self.data['SafetyTrigger'] == True:
                        self.buzzer(4000,4)
                    # Add process name to the collected variables
                    self.data['ProcessName'] = process
                    # log to database
                    self.write_to_database()
                except  Queue.Empty

            # Write to config.yaml every 3600 iterations
            if self.counter < 3600:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            # Put new variable in correct queue
            try:
                updatedvars = self.loadconfig('newvar.yaml')
                for processname, variables in updatedvars.items()
                    self.processdata[processname]['inputqueue'].put(variables)
                os.remove('newvar.yaml')
                time.sleep(1)

            except NameError:

  
if __name__ == 'main':
    BrewManager.start()

