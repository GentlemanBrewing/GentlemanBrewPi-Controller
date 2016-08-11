#!/usr/bin/python3

import multiprocessing
import datetime
import time
from ABE_ADCPi import ADCPi
import RPi.GPIO as GPIO
import sqlite3
import yaml
import Controller


# Main Manager class
class BrewManager(multiprocessing.Process):

    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.processinformation = self.loadconfig()
        self.conn = sqlite3.connect('Log.db')
        self.cur = self.conn.cursor()
        self.counter = 0

    # Function for loading config file
    def loadconfig(self):
        f = open('Config.yaml')
        datamap = yaml.safe_load(f)
        f.close()
        return datamap
  
    # Function for updating config file
    def writeconfig(data):
        f = open('Config.yaml', "w")
        yaml.dump(data, f)
        f.close()

    def buzzer(self, frequency, duration):
        #Code for buzzer here


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
        for process in self.processinformation.items():
            if process['process_variables']['terminate'] == 0:
                process['process_data']['inputqueue'] = multiprocessing.Queue()
                process['process_data']['outputqueue'] = multiprocessing.Queue()
                Controller.PIDController( process['process_data']['inputqueue'], process['process_data']['outputqueue']).start()
                process['process_data']['inputqueue'].put(process['process_variables'])

        # Main loop
        while True:

            # Get output from process and record in database
            for process in self.processinformation.items():
                self.data = process['process_data']['outputqueue'].get()
                # Check for Safetytrigger from process and sound buzzer if present
                if self.data['SafetyTrigger'] == True:
                    self.buzzer(4000,60)
                self.data['ProcessName'] = process
                self.write_to_database()

            # Write to config.yaml every 3600 iterations
            if self.counter < 3600:
                self.counter += 1
            else:
                self.counter = 0
                self.writeconfig(self.processinformation)

            # Check for changing setpoint and use interpolation function

            #

            # Put new variable in correct queue
            processname = #variable here
            self.processinformation[processname]['process_data']['inputqueue'].put(#variable here)

            time.sleep(1)


  
if __name__ == 'main':
    BrewManager.start()

