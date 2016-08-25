#! /usr/bin/env python3

import multiprocessing
import queue
import time
import RPi.GPIO as GPIO
import sqlite3
import yaml
import Controller
import Controllertester
import os
import WebServer
import copy


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
        self.counter = 0
        self.processinformation = self.loadconfig('Config.yaml')
        self.textlist = ['safety_mode', 'moutput', 'ssrmode', 'relaypin', 'terminate', 'autotune_on', 'Delete_This_Process']
        self.processdata = {}
        self.controllerdata = {}
        self.process_output = copy.deepcopy(self.processinformation)
        self.webdata = {}
        self.outputlist = ['Temperature', 'Setpoint', 'Duty', 'DateTime', 'SafetyTemp', 'SafetyTrigger', 'Status']
        self.lastsleeptime = 0

    # Function for loading config file
    def loadconfig(self, filename):
        try:
            f = open(filename)
        except FileNotFoundError:
            print('%s not found loading Default' % filename)
            defaultfilename = "Default" + filename
            f = open(defaultfilename)
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
                conn.execute('INSERT INTO PIDOutput(DateTime, ProcessName, Temperature, Duty, Setpoint,'
                                  'SafetyTemp, SafetyTrigger, Status) VALUES (:DateTime, :ProcessName,'
                                  ':Temperature, :Duty, :Setpoint, :SafetyTemp, :SafetyTrigger, :Status)', self.controllerdata)
        except sqlite3.Error:
            self.buzzer(2000, 1)

    # Main running function
    def run(self):
        # Start the buzzer process
        self.processdata['Buzzer'] = {}
        self.processdata['Buzzer']['inputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['outputqueue'] = multiprocessing.Queue()
        self.processdata['Buzzer']['inputqueue'].put(self.processinformation['Buzzer'])
        Buzzer(self.processdata['Buzzer']['inputqueue']).start()
        print('Buzzer started - BrewMan')

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
            #print('1')
            # Start new processes not already running
            for process, pvariables in self.processinformation.items():
                if pvariables['terminate'] == 'False' and process not in self.processdata.keys():
                    self.processdata[process] = {}
                    self.processdata[process]['inputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['outputqueue'] = multiprocessing.Queue()
                    self.processdata[process]['inputqueue'].put(pvariables)
                    Controller.PIDController(self.processdata[process]['inputqueue'],
                                             self.processdata[process]['outputqueue']).start()
                    print('%s started - BrewMan' % process)
                    self.buzzer(2000, 1)

            #print('2')
            # Update the process variable dictionary for the web output
            self.process_output = copy.deepcopy(self.processinformation)

            # Get output from process and record in database
            for process in self.processdata.keys():
                # Do not collect web server output here, buzzer never produces output
                if process != 'WebServ':
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
                                if outputvar != 'ProcessName':
                                    self.process_output[process][outputvar] = self.controllerdata[outputvar]
                            # log to database
                            self.write_to_database()
                        except queue.Empty:
                            break

            #print('3')
            # Send updated process_output to web server
            self.processdata['WebServ']['inputqueue'].put(self.process_output)

            #print('4')
            # Get information from webserver
            while True:
                try:
                    self.webdata = self.processdata['WebServ']['outputqueue'].get_nowait()
                    print('Data collected from webqueue - BrewManager')
                    for process in self.webdata.keys():
                        # Check if process is in current process list, create if not
                        if process not in self.processinformation.keys():
                            self.processinformation[process] = {}
                        # Check for the delete process flag
                        if self.webdata[process]['Delete_This_Process'] == 'True':
                            del self.processinformation[process]
                            self.webdata[process]['terminate'] = 'True'
                            print('delete process initiated')
                        else:
                            # Update variables for the process from the webdata while excluding the output variables
                            for pvar in self.webdata[process].keys():
                                if pvar not in self.outputlist:
                                    if type(self.webdata[process][pvar]) == dict:
                                        if pvar not in self.processinformation[process].keys():
                                            self.processinformation[process][pvar] = {}
                                        for key in self.webdata[process][pvar].keys():
                                            if pvar in self.textlist:
                                                self.processinformation[process][pvar][key] = str(self.webdata[process][pvar][key])
                                            else:
                                                self.processinformation[process][pvar][key] = float(self.webdata[process][pvar][key])
                                                self.webdata[process][pvar][key] = self.processinformation[process][pvar][key]
                                    else:
                                        if pvar in self.textlist:
                                            self.processinformation[process][pvar] = str(self.webdata[process][pvar])
                                        else:
                                            self.processinformation[process][pvar] = float(self.webdata[process][pvar])
                                            self.webdata[process][pvar] = self.processinformation[process][pvar]
                    print('Updating config file')
                    # Update the config file
                    self.counter = 0
                    self.writeconfig(self.processinformation)
                except queue.Empty:
                    break

            #print('5')
            # Put new variables from webserver in process queues if process is running
            for processname, variables in self.webdata.items():
                if processname in self.processdata.keys():
                    self.processdata[processname]['inputqueue'].put(variables)
                    print('Data in %s inputqueue - BrewManager' % processname)
                    if variables['terminate'] == 'True':
                        del self.processdata[processname]
                        print('deleted process data of %s' % processname)

            # Clear webdata
            self.webdata={}

            #print('6')
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

            #print('7')
            # Write to config.yaml every 3600 iterations
            if self.counter < 3600:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            if time.time() < self.lastsleeptime + 5:
                sleeptime = 5 -time.time() + self.lastsleeptime
            else:
                sleeptime = 0
            print('Sleeping for %s' % sleeptime)
            time.sleep(sleeptime)
            self.lastsleeptime = time.time()

        print('BrewManager exiting')

  
if __name__ == "__main__":
    man = BrewManager()
    man.start()
    man.join()