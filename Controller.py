#! /usr/bin/env python3

import multiprocessing
import queue
import datetime
import time
import RPi.GPIO as GPIO
import copy
import sqlite3


# PID Controller class
class PIDController(multiprocessing.Process):

    def __init__(self, inputqueue, outputqueue, name):
        multiprocessing.Process.__init__(self)
        print('%s PID Started' % name)
        self.safetytrigger = False

        # Use correct communication queues
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue

        # Setup variables dictionary with initial values
        self.variabledict = {
            'sleeptime': 5,
            'kp': 0,
            'ki': 0,
            'kd': 0,
            'setpoint': {
                '2016-08-12 09:00:00': 20,
                '2016-08-13 09:00:00': 20
            },
            'adcvoltage': {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0,
                7: 0,
                8: 0
            },
            'control_channel': 1,
            'control_k1': 885,
            'control_k2': 2790,
            'control_k3': 0,
            'safety_channel': 2,
            'safety_k1': 885,
            'safety_k2': 2790,
            'safety_k3': 0,
            'safety_value': 0,
            'safety_mode': "off",
            'umax': 100,
            'umin': 0,
            'moutput': "auto",
            'ssrduty': 1,
            'ssrpin': 27,
            'ssrmode': "pwm",
            'pwm_frequency': 1,
            'relayduty': {'Relay1': 0, 'Relay2': 0, 'Relay3': 0, 'Relay4': 0, 'Relay5': 0},
            'relaypin': {'Relay1': "off", 'Relay2': "off", 'Relay3': "off", 'Relay4': "off", 'Relay5': "off"},
            'terminate': 0,
            'autotune_temp': 102,
            'autotune_hysteresis': 1,
            'autotune_kp': 0,
            'autotune_ki': 0,
            'autotune_kd': 0,
            'autotune_on': 'False',
            'autotune_sleeptime': 0.1,
            'autotune_maxiterations': 20,
            'autotune_iterations': 0,
            'autotune_convergence': 0.01,
            'autotune_gainsign': 1,
            'autotune_dict': {
                'time': [],
                'temp': [],
                'output': [],
                'timeperiod': [],
                'peaktype': 'max',
                'startrange': 0,
                'timeperiodstart': 0,
                'relayofftime': 0
            },
            'autotune_peaks': {
                'max': {},
                'min': {}
            }
        }

        # Initialize required variables
        self.name = name
        self.setpoint = 0
        self.setpointchanges = 2
        self.output = 0
        self.maxoutput = 0
        self.outputdict = {}
        self.outputdict['Status'] = 'PID Controller Started'

    # Function for interpolating setpoint
    def setpoint_interpolate(self):
        timelist = []
        valuelist = []
        for time, value in sorted(self.variabledict['setpoint'].items()):
            timelist.append(time)
            valuelist.append(value)
        setpointchanges = len(timelist) - 1
        timenow = datetime.datetime.now()

        if timenow < datetime.datetime.strptime(timelist[0], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = "off"
        elif timenow == datetime.datetime.strptime(timelist[0], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = valuelist[0]
        elif timenow >= datetime.datetime.strptime(timelist[setpointchanges], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = "off"
        else:
            self.setpoint = "off"
            for x in range(setpointchanges, -1, -1):
                # Check for current timeframe and adjust setpoint by interpolation
                if datetime.datetime.strptime(timelist[x], '%Y-%m-%d %H:%M:%S') < timenow:
                    time1 = datetime.datetime.strptime(timelist[x], '%Y-%m-%d %H:%M:%S')
                    value1 = valuelist[x]
                    time2 = datetime.datetime.strptime(timelist[x+1], '%Y-%m-%d %H:%M:%S')
                    value2 = valuelist[x+1]
                    self.setpoint = ((timenow - time1) / (time2 - time1)) * (value2 - value1)  + value1
                    break

    # Autotune function
    def autotune(self):
        if self.variabledict['autotune_iterations'] == 0:
            self.variabledict['sleeptime'] = self.variabledict['autotune_sleeptime']
            self.variabledict['umin'] = 0
            self.variabledict['umax'] = 100
            self.variabledict['moutput'] = 0
            self.outputdict['Status'] = 'Autotune started'

        # Read New Measured Variable
        mvchannel = int(self.variabledict['control_channel'])
        v = float(self.variabledict['adcvoltage'][mvchannel])
        mv = self.variabledict['control_k1'] * v * v + self.variabledict['control_k2'] * v + self.variabledict['control_k3']

        # Do assymetric relay output
        if self.variabledict['autotune_gainsign'] >= 0:
            if mv <= self.variabledict['autotune_temp'] - self.variabledict['autotune_hysteresis'] and self.variabledict['moutput'] == 0:
                print('relay on')
                self.variabledict['moutput'] = 100
                self.variabledict['autotune_iterations'] += 1
            elif mv >= self.variabledict['autotune_temp'] + self.variabledict['autotune_hysteresis'] and self.variabledict['moutput'] == 100:
                print('relay off')
                self.variabledict['moutput'] = 0
                self.variabledict['autotune_iterations'] += 1
        else:
            if mv <= self.variabledict['autotune_temp'] - self.variabledict['autotune_hysteresis'] and self.variabledict['moutput'] == 100:
                print('relay off')
                self.variabledict['moutput'] = 0
                self.variabledict['autotune_iterations'] += 1
            elif mv >= self.variabledict['autotune_temp'] + self.variabledict['autotune_hysteresis'] and self.variabledict['moutput'] == 0:
                print('relay on')
                self.variabledict['moutput'] = 100
                self.variabledict['autotune_iterations'] += 1

        self.outputdict['Status'] = 'Autotune in progress - %s of %s' % (self.variabledict['autotune_iterations'], self.variabledict['autotune_maxiterations'])
        # Update autotunedict
        self.variabledict['autotune_dict']['time'].append(time.time())
        self.variabledict['autotune_dict']['temp'].append(mv)
        self.variabledict['autotune_dict']['output'].append(self.variabledict['moutput'])


        if len(self.variabledict['autotune_dict']['output']) == 1:
            if self.variabledict['autotune_dict']['output'][0] == 100:
                self.variabledict['autotune_dict']['peaktype'] = 'min'
                self.variabledict['autotune_dict']['startrange'] = 0
                self.variabledict['autotune_dict']['timeperiodstart'] = self.variabledict['autotune_dict']['time'][0]
        else:
            if self.variabledict['autotune_dict']['output'][-1] != self.variabledict['autotune_dict']['output'][-2]:
                endrange = len(self.variabledict['autotune_dict']['output'])
                startrange = self.variabledict['autotune_dict']['startrange']
                # Determine Peak type
                if self.variabledict['autotune_dict']['output'][-1] == 100:
                    self.variabledict['autotune_dict']['peaktype'] = 'max'
                    peaktemp = max(self.variabledict['autotune_dict']['temp'][startrange:endrange])
                    peaktempslot = self.variabledict['autotune_dict']['temp'].index(peaktemp)
                    peaktime = self.variabledict['autotune_dict']['time'][peaktempslot]
                    self.variabledict['autotune_peaks']['max'][peaktime] = peaktemp
                    # prepare variables for convergence test
                    periodstart = self.variabledict['autotune_dict']['timeperiodstart']
                    periodend = self.variabledict['autotune_dict']['time'][-1]
                    periodlength = periodend - periodstart
                    self.variabledict['autotune_dict']['timeperiod'].append(periodlength)
                    self.variabledict['autotune_dict']['timeperiodstart'] = self.variabledict['autotune_dict']['time'][-1]
                else:
                    self.variabledict['autotune_dict']['peaktype'] = 'min'
                    peaktemp = min(self.variabledict['autotune_dict']['temp'][startrange:endrange])
                    peaktempslot = self.variabledict['autotune_dict']['temp'].index(peaktemp)
                    peaktime = self.variabledict['autotune_dict']['time'][peaktempslot]
                    self.variabledict['autotune_peaks']['min'][peaktime] = peaktemp
                    self.variabledict['autotune_dict']['relayofftime'] = self.variabledict['autotune_dict']['time'][-1]


                # Check for convergence
                if len(self.variabledict['autotune_dict']['timeperiod']) > 1:
                    newlength = self.variabledict['autotune_dict']['timeperiod'][-1]
                    oldlength = self.variabledict['autotune_dict']['timeperiod'][-2]
                    conv = abs((newlength - oldlength) / oldlength)
                    if conv < self.variabledict['autotune_convergence']:
                        # Converged
                        self.variabledict['autotune_on'] = 'False'
                        self.outputdict['Status'] = 'Autotuner converged - Terminating'
                        self.variabledict['terminate'] = 'True'
                        # Write the data to database
                        conn = sqlite3.connect('Autotune.db')
                        dboutput = {}
                        for i in range(len(self.variabledict['autotune_dict']['time'])):
                            dboutput['Time'] = self.variabledict['autotune_dict']['time'][i]
                            dboutput['Temp'] = self.variabledict['autotune_dict']['temp'][i]
                            dboutput['Output'] = self.variabledict['autotune_dict']['output'][i]
                            try:
                                with conn:
                                    conn.execute('INSERT INTO autotune(Time, Temp, Output) VALUES'
                                                 ' (:Time, :Temp, :Output)', dboutput)
                            except sqlite3.IntegrityError:
                                pass
                        # todo Create Autotuner class - Complete the autotune procedure

                        # d1 = ((self.variabledict['autotune_dict']['time'][-1] - self.variabledict['autotune_dict']['relayofftime']) / newlength) * self.maxoutput
                        # d2 = self.maxoutput - d1
                        # self.outputdict['kp'] = ""
                        # self.outputdict['ki'] = ""
                        # self.outputdict['kd'] = ""


        if self.variabledict['autotune_iterations'] >= self.variabledict['autotune_maxiterations']:
            self.variabledict['autotune_on'] = 'False'
            self.outputdict['Status']= 'Autotuner failed to converge - Terminating'
            self.outputdict['autotune_on'] = 'False'
            self.outputdict['terminate'] = 'True'
            self.variabledict['terminate'] = 'True'




    # Main looping function of the PID Controller
    def run(self):

        # Get updated variables from queue
        try:
            while True:
                updated_variables = self.inputqueue.get_nowait()
                for variable, value in updated_variables.items():
                    self.variabledict[variable] = value
        except queue.Empty:
            pass

        # Initialize variables
        e = 0
        e1 = 0
        max_relay_output = 0
        relaystate = {}
        relayduty = self.variabledict['relayduty']

        for relay in relayduty.keys():
            relaystate[relay] = 0
        relayoutput = 0
        GPIO.setmode(GPIO.BCM)
        relaypin = self.variabledict['relaypin']

        # setup GPIO
        GPIO.setup(int(self.variabledict['ssrpin']), GPIO.OUT)
        if self.variabledict['ssrmode'] == 'pwm':
            pwm = GPIO.PWM(int(self.variabledict['ssrpin']), 1)
            pwm.start(0)

        # Set GPIO pins as outputs
        for relay in sorted(relaypin.keys()):
            if relaypin[relay] != "off":
                GPIO.setup(int(relaypin[relay]), GPIO.OUT)

        # Main control loop
        while True:

            # Check for updated variables
            try:
                while True:
                    updated_variables = self.inputqueue.get_nowait()
                    for variable, value in updated_variables.items():
                        self.variabledict[variable] = value
            except queue.Empty:
                pass

            # Check terminate variable
            if self.variabledict['terminate'] == 'True':
                self.outputdict['Status'] = 'PID Controller Terminating'
                break

            # Update Variables
            relayduty = self.variabledict['relayduty']
            ssrduty = self.variabledict['ssrduty']

            # Determine maximum output
            for relay in sorted(relayduty.keys()):
                max_relay_output += relayduty[relay]
            self.maxoutput = self.variabledict['ssrduty'] * .99 + max_relay_output

            # Get new setpoint based on current date and time
            self.setpoint_interpolate()

            # Check for autotune
            if self.variabledict['autotune_on'] == 'True':
                self.autotune()

            # Update control parameters
            k1 = self.variabledict['kp'] + self.variabledict['ki'] + self.variabledict['kd']
            k2 = - self.variabledict['ki'] - 2 * self.variabledict['kd']
            k3 = self.variabledict['kd']
            sp = self.setpoint
            u = self.output

            # Read New Measured Variable
            mvchannel = int(self.variabledict['control_channel'])
            v = float(self.variabledict['adcvoltage'][mvchannel])
            mv = self.variabledict['control_k1'] * v * v + self.variabledict['control_k2'] * v + self.variabledict['control_k3']

            # Check if setpoint is active and calculate control output if it is
            if self.setpoint != "off":
                # Update error variables
                e2 = e1
                e1 = e
                e = sp - mv

                delta_u = k1 * e + k2 * e1 + k3 * e2
                u += delta_u
            else:
                u = 0

            # check for manual mode
            if self.variabledict['moutput'] != "auto":
                #self.outputdict['Status'] = 'Manual Mode Active'
                u = float(self.variabledict['moutput'])
            else:
                #self.outputdict['Status'] = 'PID Control Active'

            # clamp output to between min and max values
            if u > self.variabledict['umax']:
                u = self.variabledict['umax']
            elif u < self.variabledict['umin']:
                u = self.variabledict['umin']

            # Check safety variable
            if self.variabledict['safety_mode'] != "off":
                svchannel = int(self.variabledict['safety_channel'])
                sv = float(self.variabledict['adcvoltage'][svchannel])
                safetytemp = self.variabledict['safety_k1'] * sv * sv + self.variabledict['safety_k2'] * sv + self.variabledict['safety_k3']

                if self.variabledict['safety_mode'] == "max" and self.variabledict['safety_value'] > safetytemp:
                    u = 0
                    self.safetytrigger = True
                elif self.variabledict['safety_mode'] == "min" and self.variabledict['safety_value'] < safetytemp:
                    u = 0
                    self.safetytrigger = True
            else:
                safetytemp = "off"

            self.output = u
            duty = u / self.variabledict['umax'] * 100

            # Determine current output
            for relay in sorted(relayduty.keys()):
                relayoutput += relaystate[relay] * relayduty[relay]

            # Determine Required Output
            output = duty /100 * self.maxoutput

            # Check which relays should be switched on or off
            # If at max duty all should be on
            if duty == 100:
                for relay in sorted(relayduty.keys()):
                    relaystate[relay] = 1

            # Relays produce too much output-switch relays off until relays produce less output than the desired output
            elif relayoutput > output:
                for relay in sorted(relayduty.keys(), reverse=True):
                    relayoutput -= relaystate[relay] * relayduty[relay]
                    relaystate[relay] = 0
                    if relayoutput < output:
                        break

            # Relays produce too little output-switch relays on until relays produce enough output
            elif relayoutput + ssrduty < output:
                for relay in sorted(relayduty.keys()):
                    if relaystate[relay] == 0:
                        relaystate[relay] = 1
                        relayoutput += relayduty[relay]
                        if relayoutput + ssrduty > output:
                            break

            # Calculate PWM duty needed from ssr
            ssroutput = output - relayoutput
            ssr_pwmduty = (ssroutput * 100) // ssrduty

            # Activate pins to switch relays
            for relay in sorted(relaypin.keys()):
                if relaypin[relay] != "off":
                    GPIO.output(int(relaypin[relay]), relaystate[relay])

            # Change ssr PWM
            if self.variabledict['ssrmode'] == 'pwm':
                pwm.ChangeFrequency(self.variabledict['pwm_frequency'])
                pwm.ChangeDutyCycle(ssr_pwmduty)
            elif self.variabledict['ssrmode'] == 'relay':
                if ssr_pwmduty > 50:
                    GPIO.output(int(self.variabledict['ssrpin']), 1)
                else:
                    GPIO.output(int(self.variabledict['ssrpin']), 0)

            # Update output dictionary
            self.outputdict['DateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.outputdict['Temperature'] = mv
            self.outputdict['Duty'] = duty
            self.outputdict['Setpoint'] = self.setpoint
            self.outputdict['SafetyTemp'] = safetytemp
            self.outputdict['SafetyTrigger'] = self.safetytrigger

            # Send output to Manager
            self.outputqueue.put(self.outputdict)

            # Wait before running loop again
            time.sleep(self.variabledict['sleeptime'])

        # Ensure GPIO is cleaned up before exiting loop
        GPIO.cleanup()
        print('%s exiting' % self.name)