#! /usr/bin/env python3

import multiprocessing
import queue
import time
import RPi.GPIO as GPIO
import sqlite3
import yaml
import Controller
import os
import WebServer


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
        self.controllerdata = {}
        self.process_output = self.processinformation
        self.webdata = {}

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
                                  ':Temperature, :Duty, :Setpoint, :SafetyTemp, :SafetyTrigger)', self.controllerdata)
        except sqlite3.IntegrityError:
            self.buzzer(2000, 1)

    # Main running function
    def run(self):
        # Start the buzzer process
        self.processdata['Buzzer'] = {}
        self.processdata['Buzzer']['inputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['outputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['inputqueue'].put(self.processinformation['Buzzer'])
        Buzzer(self.processdata['Buzzer']['inputqueue']).start()

        # Start the web server process
        self.processdata['WebServ'] = {}
        self.processdata['WebServ']['inputqueue'] = multiprocessing.Queue()
        self.processdata['WebServ']['outputqueue'] = multiprocessing.Queue()
        self.processdata['WebServ']['inputqueue'].put(self.process_output)
        webserver = multiprocessing.Process(target=WebServer.main, args=(self.processdata['WebServ']['inputqueue'], self.processdata['WebServ']['outputqueue']))
        webserver.start()

        # Main loop
        while True:

            # Start new processes not already running
            for process, pvariables in self.processinformation.items():
                if pvariables['terminate'] == 0 and process in self.processdata.keys() is False:
                    self.processdata[process] = {}
                    self.processdata[process]['inputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['outputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['inputqueue'].put(pvariables)
                    Controller.PIDController(self.processdata[process]['inputqueue'],
                                             self.processdata[process]['outputqueue']).start()
                    self.buzzer(2000, 1)

            # Update the dictionary for the web output
            self.process_output = self.processinformation
            # Get output from process and record in database
            for process in self.processdata.keys():
                while True:
                    try:
                        self.controllerdata = self.processdata[process]['outputqueue'].get_nowait()
                        # Check for Safetytrigger from process and sound buzzer if present
                        if self.controllerdata['SafetyTrigger'] == True:
                            self.buzzer(3500, 3)
                        # Add process name to the collected variables
                        self.controllerdata['ProcessName'] = process
                        # Record the output variables in process_output for web server
                        for outputvar in self.controllerdata.keys():
                            self.process_output[process][outputvar] = self.controllerdata[outputvar]
                        # log to database
                        self.write_to_database()
                    except queue.Empty:
                        break

            # Send updated process_output to web server
            self.processdata['WebServ']['inputqueue'].put(self.process_output)

            # Get information from webserver
            while True:
                try:
                    self.webdata = self.processdata['WebServ']['outputqueue'].get_nowait()
                    for process in self.webdata.keys():
                        if process in self.processinformation.keys() is False:
                            self.processinformation[process] = {}
                        for pvar in self.webdata[process].keys():
                            self.processinformation[process][pvar] = self.webdata[process][pvar]
                except queue.Empty:
                    break

            # Put new variables from webserver in process queues if process is running
            for processname, variables in self.webdata.items():
                if processname in self.processdata.keys() is True:
                    self.processdata[processname]['outputqueue'].put(variables)

            # Put new variable from newvar.yaml in correct queue
            try:
                f = open('newvar.yaml')
                updatedvars = yaml.safe_load(f)
                f.close()
                for processname, variables in updatedvars.items():
                    self.processdata[processname]['inputqueue'].put(variables)
                os.remove('newvar.yaml')
            except FileNotFoundError:
                pass

            # Write to config.yaml every 3600 iterations
            if self.counter < 3600:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            time.sleep(1)





  
if __name__ == "__main__":
    man = BrewManager()
    man.start()
    man.join()
