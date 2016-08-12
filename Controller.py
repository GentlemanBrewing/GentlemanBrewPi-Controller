#!/usr/bin/python3

import multiprocessing
import datetime
import time
from ABE_ADCPi import ADCPi
import RPi.GPIO as GPIO


# PID Controller class
class PIDController(multiprocessing.Process):

    def __init__(self, inputqueue, outputqueue):
        multiprocessing.Process.__init__(self)
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
                'time': ['2016-08-12 09:00:00', '2016-08-13 09:00:00'],
                'value': [20, 20]
            },
            'control_channel': 1,
            'control_k1': 0,
            'control_k2': 27,
            'control_k3': 0,
            'safety_channel': 2,
            'safety_k1': 0,
            'safety_k2': 27,
            'safety_k3': 0,
            'safety_value': 0,
            'safety_mode': "off",
            'umax': 0,
            'umin': 0,
            'moutput': "auto",
            'ssrduty': 1,
            'ssrpin': 4,
            'ssrmode': "pwm",
            'pwm_frequency': 1,
            'relayduty': {'Relay1': 0, 'Relay2': 0, 'Relay3': 0, 'Relay4': 0, 'Relay5': 0},
            'relaypin': {'Relay1': 0, 'Relay2': 0, 'Relay3': 0, 'Relay4': 0, 'Relay5': 0},
            'terminate': 0
        }

        # Initialize required variables
        self.output = 0
        self.setpoint = 0
        self.setpointchanges = 2
        self.outputdict = {}

    # Function for interpolating setpoint
    def setpoint_interpolate(self):
        timelist = self.variabledict['setpoint']['time']
        valuelist = self.variabledict['setpoint']['value']
        setpointchanges = len(timelist)
        timenow = datetime.datetime.now()

        if timenow < datetime.datetime.strptime(timelist[0], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = "off"
        elif timenow == datetime.datetime.strptime(timelist[0], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = valuelist[0]
        elif timenow >= datetime.datetime.strptime(timelist[setpointchanges], '%Y-%m-%d %H:%M:%S'):
            self.setpoint = "off"
        else:
            self.setpoint = "off"
            for x in range(setpointchanges, 0):
                # Check for current timeframe and adjust setpoint by interpolation
                if datetime.datetime.strptime(timelist[x], '%Y-%m-%d %H:%M:%S') < timenow:
                    time1 = datetime.datetime.strptime(timelist[x], '%Y-%m-%d %H:%M:%S')
                    value1 = valuelist[x]
                    time2 = datetime.datetime.strptime(timelist[x+1], '%Y-%m-%d %H:%M:%S')
                    value2 = valuelist[x+1]
                    self.setpoint = ((timenow - time1) / (time2 - time1)) * (value2 - value1)  + value1
                    break

                #

    # Main looping function of the PID Controller
    def run(self):

        # Initialize variables
        e = 0
        e1 = 0

        relayduty = self.variabledict['relayduty']
        relaypin = self.variabledict['relaypin']
        ssrduty = self.variabledict['ssrduty']
        max_relay_output = 0
        relaystate = {}
        for relay, in relayduty.items():
            relaystate = {relay: 0}
        relayoutput = 0
        GPIO.setmode(GPIO.BCM)
        pwm = GPIO.PWM(self.variabledict['ssrpin'], 1)
        pwm.start(0)

        # Set GPIO pins as outputs
        for relay in sorted(relaypin.keys()):
            GPIO.setup(relaypin[relay], GPIO.out)

        # Determine maximum output
        for relay in sorted(relayduty.keys()):
            max_relay_output += relayduty[relay]
        max_output = self.variabledict['ssrduty'] + max_relay_output

        # Main control loop
        while True:

            # Check for updated variables
            try:
                updated_variables = self.inputqueue.get()
                for variable, value in updated_variables.items():
                    self.variabledict[variable] = value
            except Queue.Empty:

            #Get new setpoint based on current date and time
            self.setpoint_interpolate()

            # Check if setpoint is active and calculate control output if it is
            if self.setpoint != "off":
                # Update control parameters
                k1 = self.variabledict['kp'] + self.variabledict['ki'] + self.variabledict['kd']
                k2 = - self.variabledict['ki'] - 2 * self.variabledict['kd']
                k3 = self.variabledict['kd']
                sp = self.setpoint
                u = self.output

                # Read New Measured Variable
                mvchannel = self.variabledict['control_channel']
                v = ADCPi.read_voltage(mvchannel)
                mv = self.variabledict['control_k1'] * v * v + self.variabledict['control_k2'] * v + self.variabledict['control_k3']

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
                u = self.variabledict['moutput']

            # clamp output to between min and max values
            if u > self.variabledict['umax']:
                u = self.variabledict['umax']
            elif u < self.variabledict['umin']:
                u = self.variabledict['umin']

            # Check safety variable
            if self.variabledict['safety_mode'] != "off":
                svchannel = self.variabledict['safety_channel']
                sv = ADCPi.read_voltage(svchannel)
                safetytemp = self.variabledict['safety_k1'] * sv * sv + self.variabledict['safety_k2'] * sv + self.variabledict['safety_k3']

                if self.variabledict['safety_mode'] == "max" and self.variabledict['safety_value'] > safetytemp:
                    u = 0
                    self.safetytrigger = True
                elif self.variabledict['safety_mode'] == "min" and self.variabledict['safety_value'] < safetytemp:
                    u = 0
                    self.safetytrigger = True
            else:
                safetytemp = "off"

            duty = u / self.variabledict['umax']

            # Determine current output
            for relay in sorted(relayduty.keys()):
                relayoutput += relaystate[relay] * relayduty[relay]

            # Determine Required Output
            output = duty * max_output

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
            ssr_pwmduty = ssroutput / ssrduty * 100

            # Activate pins to switch relays
            for relay in sorted(relaypin.keys()):
                GPIO.output(relaypin[relay], relaystate[relay])

            # Change ssr PWM
            pwm.ChangeDutyCycle(ssr_pwmduty)

            # Update output dictionary
            self.outputdict['DateTime'] = datetime.datetime.now()
            self.outputdict['Temperature'] = mv
            self.outputdict['Duty'] = duty
            self.outputdict['Setpoint'] = sp
            self.outputdict['SafetyTemp'] = safetytemp
            self.outputdict['SafetyTrigger'] = self.safetytrigger

            # Send output to Manager
            self.outputqueue.put(self.outputdict)

            # Check terminate variable
            if self.variabledict['terminate'] == 1:
                break

            # Wait before running loop again
            time.sleep(self.variabledict['sleeptime'])

    # Ensure GPIO is cleaned up before exiting loop
    GPIO.cleanup()
