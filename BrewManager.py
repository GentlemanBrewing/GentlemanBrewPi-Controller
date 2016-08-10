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
        self.processinformation = loadconfig(self)
        self.conn = sqlite3.connect('Log.db')
        self.cur = self.conn.cursor()

    # Function for loading config file
    def loadconfig(self):
        f = open('Config.yaml')
        datamap = yaml.safe_load(f)
        f.close
        return datamap
  
    # Function for updating config file
    def writeconfig(data):
        f = open('Config.yaml', "w")
        yaml.dump(data, f)
        f.close

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
                if self.data['SafetyTrigger'] == True:
                    self.buzzer(4000,60)
                self.data['ProcessName'] = process
                self.write_to_database()

            # Put new variable in correct queue
                processname = #variable here
                self.processinformation[processname]['process_data']['inputqueue'].put(#variable here)




  
if __name__ == 'main':
    BrewManager.start()

