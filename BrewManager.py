#! /usr/bin/env python3

import multiprocessing
import queue
import time
import TestRPi.GPIO as GPIO
import sqlite3
import yaml
#from ABE_ADCPi import ADCPi
#from ABE_Helpers import ABEHelpers
import Controller
import os
import WebServer
import copy
import random


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
                GPIO.setup(self.variabledict['pin'], GPIO.OUT)
                p = GPIO.PWM(self.variabledict['pin'], self.variabledict['frequency'])
                p.start(self.variabledict['duty'])
                time.sleep(self.variabledict['duration'])
                p.stop()
                self.variabledict['duration'] = 0
                GPIO.cleanup()

            time.sleep(1)


class ADCReader(multiprocessing.Process):

    def __init__(self, inputqueue, outputqueue):
        multiprocessing.Process.__init__(self)

        # Use correct communication queues
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue

        # Declare variables
        self.adcdict = {}
        self.sleeptime = 1
        self.bitrate = 18
        self.addr1 = 0x68
        self.addr2 = 0x69

        # Configure ADC correctly
        #self.i2c_helper = ABEHelpers()
        #self.bus = self.i2c_helper.get_smbus()
        #self.adc = ADCPi(self.bus, self.addr1, self.addr2, self.bitrate)
        #self.adc.set_pga(8)

    def testvalues(self, input):
        output = input + random.uniform(-1, 1)
        return output


    def run(self):
        while True:

            # Ensure proper wait time between queries
            if self.bitrate == 18:
                self.sleeptime = 1 / 3
            elif self.bitrate == 16:
                self.sleeptime = 1 / 14
            elif self.bitrate == 14:
                self.sleeptime = 1 / 50
            elif self.bitrate == 12:
                self.sleeptime = 1 / 200

            for x in range(1,5):
                self.adcdict[x] = self.testvalues(x)
                time.sleep(0.1)
                self.adcdict[x+4] = self.testvalues(x+4)
                self.outputqueue.put(self.adcdict)
                time.sleep(self.sleeptime)




# Class for writing to Database
class WriteToDatabase(multiprocessing.Process):

    def __init__(self, inputqueue, outputqueue):
        multiprocessing.Process.__init__(self)

        # Use correct communication queues
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue

        #initialize variables
        self.databaselist = []
        self.lastsleeptime = 0

    def write_to_database(self):
        conn = sqlite3.connect('Log.db')
        try:
            with conn:
                conn.executemany('INSERT INTO PIDOutput(DateTime, ProcessName, Temperature, Duty, Setpoint,'
                                 'SafetyTemp, SafetyTrigger, Status) VALUES (:DateTime, :ProcessName,'
                                 ':Temperature, :Duty, :Setpoint, :SafetyTemp, :SafetyTrigger, :Status)',
                                 self.databaselist)
        except sqlite3.Error:
            pass
        self.databaselist = []

    def run(self):

        while True:

            # Get updated variables from queue
            try:
                while True:
                    updated_variables = self.inputqueue.get_nowait()
                    self.databaselist.append(updated_variables)
            except queue.Empty:
                pass

            # Check length of list to write
            if len(self.databaselist) > 50:
                self.write_to_database()

            time.sleep(2)



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
        self.adcdata = {'adcvoltage': {}}
        self.process_output = copy.deepcopy(self.processinformation)
        self.webdata = {}
        self.outputlist = ['Temperature', 'Setpoint', 'Duty', 'DateTime', 'SafetyTemp', 'SafetyTrigger', 'Status']
        self.nonpidlist = ['Buzzer', 'WebServ', 'DBServ', 'ADCReader']
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
        print('Webserver started - BrewMan')

        # Start the Database manager
        self.processdata['DBServ'] = {}
        self.processdata['DBServ']['inputqueue'] = multiprocessing.Queue()
        self.processdata['DBServ']['outputqueue'] = multiprocessing.Queue()
        WriteToDatabase(self.processdata['DBServ']['inputqueue'], self.processdata['DBServ']['outputqueue']).start()
        print('DB Server started - BrewMan')

        # Start the ADC Reader
        self.processdata['ADCReader'] = {}
        self.processdata['ADCReader']['inputqueue'] = multiprocessing.Queue()
        self.processdata['ADCReader']['outputqueue'] = multiprocessing.Queue()
        ADCReader(self.processdata['ADCReader']['inputqueue'], self.processdata['ADCReader']['outputqueue']).start()
        print('ADC Reader started - BrewMan')


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
                            if process == 'ADCReader':
                                self.adcdata['adcvoltage']= self.controllerdata
                            else:
                                if self.controllerdata['SafetyTrigger'] == True:
                                    self.buzzer(3500, 3)
                                # Add process name to the collected variables
                                self.controllerdata['ProcessName'] = process
                                # Record the output variables in process_output for web server
                                for outputvar in self.controllerdata.keys():
                                    if outputvar != 'ProcessName':
                                        self.process_output[process][outputvar] = self.controllerdata[outputvar]
                                # log to database
                                self.processdata['DBServ']['inputqueue'].put(self.controllerdata)
                        except queue.Empty:
                            break

            # Send updated ADC data to processes
            for process in self.processdata.keys():
                if process not in self.nonpidlist:
                    self.processdata[process]['inputqueue'].put(self.adcdata)

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

            # looptime = 2
            #
            # if time.time() < self.lastsleeptime + looptime:
            #     sleeptime = looptime -time.time() + self.lastsleeptime
            # else:
            #     sleeptime = 0
            # print('BrewMan Sleeping for %s' % sleeptime)
            # time.sleep(sleeptime)
            # self.lastsleeptime = time.time()
            time.sleep(0.5)

        print('BrewManager exiting')

  
if __name__ == "__main__":
    man = BrewManager()
    man.start()
    man.join()