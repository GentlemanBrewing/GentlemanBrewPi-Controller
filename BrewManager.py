#!/usr/bin/python3

import multiprocessing
import queue
import time
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

    def run(self):
        while True:
            # Check for new input
            while True:
                try:
                    updated_variables = self.inputqueue.get_nowait()
                    for variable, value in updated_variables.items():
                        self.variabledict[variable] = value
                except queue.Empty:
                    break
                    pass

            if self.variabledict['duration'] != 0:
                print("Buzzing")
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.variabledict['pin'], GPIO.OUT)
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
        self.data = {}
        self.process_output = {}

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
                self.processdata[process] = {}
                self.processdata[process]['inputqueue'] = multiprocessing.Queue()
                self.processdata[process]['outputqueue'] = multiprocessing.Queue()
                self.processdata[process]['inputqueue'].put(pvariables)
                Controller.PIDController(self.processdata[process]['inputqueue'], self.processdata[process]['outputqueue']).start()

        # Create buzzer process
        self.processdata['Buzzer'] = {}
        self.processdata['Buzzer']['inputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['outputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['inputqueue'].put(self.processinformation['Buzzer'])
        Buzzer(self.processdata['Buzzer']['inputqueue']).start()

        # Main loop
        while True:

            # Get output from process and record in database
            for process in self.processdata.keys():
                while True:
                    try:
                        self.data = self.processdata[process]['outputqueue'].get_nowait()
                        # Check for Safetytrigger from process and sound buzzer if present
                        if self.data['SafetyTrigger'] == True:
                            self.buzzer(4000, 4)
                        # Add process name to the collected variables
                        self.data['ProcessName'] = process
                        # Record in process_output
                        self.process_output[process] = self.data['Temperature']
                        # log to database
                        self.write_to_database()
                        # Update the web server
                        # Code here
                    except queue.Empty:
                        break
                        pass

            # Write to config.yaml every 3600 iterations
            if self.counter < 30:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            # Put new variable in correct queue
            try:
                f = open('newvar.yaml')
                updatedvars = yaml.safe_load(f)
                f.close()
                for processname, variables in updatedvars.items():
                    self.processdata[processname]['inputqueue'].put(variables)
                os.remove('newvar.yaml')
            except FileNotFoundError:
                pass
            time.sleep(1)





  
if __name__ == "__main__":
    man = BrewManager()
    man.start()
    man.join()
