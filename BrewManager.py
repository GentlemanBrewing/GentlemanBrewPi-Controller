#! /usr/bin/env python3

import multiprocessing
import queue
import time
#import RPi.GPIO as GPIO
import sqlite3
import yaml
#import Controller
import Controllertester
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
        #GPIO.setmode(GPIO.BCM)

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
                #GPIO.setmode(GPIO.BCM)
                #GPIO.setup(self.variabledict['pin'], GPIO.OUT)
                #p = GPIO.PWM(self.variabledict['pin'], self.variabledict['frequency'])
                #p.start(self.variabledict['duty'])
                time.sleep(self.variabledict['duration'])
                #p.stop()
                self.variabledict['duration'] = 0
                #GPIO.cleanup()

            time.sleep(1)


# Main Manager class
class BrewManager(multiprocessing.Process):

    # Explanation of dictionaries:
    # processdata contains all the running processes and their communication queues
    # processinformation contains the variables for each process
    # controllerdata contains the outputs recieved from the PID Controllers
    # process_output contains both the variables and outputs for each of the PID processes
    # webdata contains the output from the web server


    def __init__(self):
        multiprocessing.Process.__init__(self)
        #self.conn = sqlite3.connect('NewLog.db')
        #self.cur = self.conn.cursor()
        self.counter = 0
        self.processinformation = self.loadconfig('Config.yaml')
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
        conn = sqlite3.connect('Log.db')
        try:
            with conn:
                print(self.controllerdata)
                conn.execute('INSERT INTO PIDOutput(DateTime, ProcessName, Temperature, Duty, Setpoint,'
                                  'SafetyTemp, SafetyTrigger) VALUES (:DateTime, :ProcessName,'
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
        webserv = multiprocessing.Process(target=WebServer.main, args=(self.processdata['WebServ']['inputqueue'], self.processdata['WebServ']['outputqueue']))
        webserv.start()
        print('webserver started - BrewMan')


        # Main loop
        while True:
            print('point1')
            # Start new processes not already running
            for process, pvariables in self.processinformation.items():
                if pvariables['terminate'] == 0 and process not in self.processdata.keys():
                    self.processdata[process] = {}
                    self.processdata[process]['inputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['outputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['inputqueue'].put(pvariables)
                    Controllertester.PIDControllertester(self.processdata[process]['inputqueue'],
                                             self.processdata[process]['outputqueue']).start()
                    self.buzzer(2000, 1)

            print('point2')
            # Update the dictionary for the web output
            self.process_output = self.processinformation
            # Get output from process and record in database
            print('point2.1')
            for process in self.processdata.keys():
                # Do not collect web server output here, buzzer never produces output
                print('point2.2')
                if process != 'WebServ':
                    print('point2.3')
                    while True:
                        try:
                            print('point2.4')
                            self.controllerdata = self.processdata[process]['outputqueue'].get_nowait()
                            # Check for Safetytrigger from process and sound buzzer if present
                            print('point2.4.1')
                            if self.controllerdata['SafetyTrigger'] == True:
                                self.buzzer(3500, 3)
                            print('point2.4.2')
                            # Add process name to the collected variables
                            print('point2.4.3')
                            self.controllerdata['ProcessName'] = process
                            # Record the output variables in process_output for web server
                            print('point2.4.4')
                            for outputvar in self.controllerdata.keys():
                                self.process_output[process][outputvar] = self.controllerdata[outputvar]
                            # log to database
                            print('point2.4.5')
                            print(self.controllerdata)
                            self.write_to_database()
                            print('point2.4.6')
                        except queue.Empty:
                            print('point2.5')
                            break

            print('point3')
            # Send updated process_output to web server
            self.processdata['WebServ']['inputqueue'].put(self.process_output)
            print('sent output to webserver')
            print(self.process_output)

            print('point4')
            # Get information from webserver
            while True:
                try:
                    self.webdata = self.processdata['WebServ']['outputqueue'].get_nowait()
                    for process in self.webdata.keys():
                        # Check if process is in current process list, create if not
                        if process not in self.processinformation.keys():
                            self.processinformation[process] = {}
                        # Update variables for the process from the webdata
                        for pvar in self.webdata[process].keys():
                            self.processinformation[process][pvar] = self.webdata[process][pvar]
                except queue.Empty:
                    break

            print('point5')
            # Put new variables from webserver in process queues if process is running
            for processname, variables in self.webdata.items():
                if processname in self.processdata.keys():
                    self.processdata[processname]['outputqueue'].put(variables)
                    if variables['terminate'] == 1:
                        del self.processdata[processname]

            print('point6')
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

            print('point7')
            # Write to config.yaml every 3600 iterations
            if self.counter < 3600:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            print('point8')
            time.sleep(5)
            print('Brewmanager done sleeping')

        print('BrewManager exiting')




  
if __name__ == "__main__":
    man = BrewManager()
    man.start()
    man.join()