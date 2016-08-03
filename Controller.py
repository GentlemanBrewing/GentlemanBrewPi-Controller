#!/usr/bin/python3

import multiprocessing
import time
from Readvoltage import ADCTEMP
import RPi.GPIO as GPIO

# PID Controller class
class PIDController(multiprocessing.Process):

    def __init__(self, inputqueue, outputqueue):
        multiprocessing.Process.__init__(self)
        self.adc = ADCTEMP()

        # Use correct communication queues
        self.inputqueue = inputqueue
        self.outputqueue = outputqueue

        # Setup variables dictionary with initial values
        self.variabledict = {
            'kp': 0,
            'ki': 0,
            'kd': 0,
            'setpoint': 0,
            'input_channel': 1,
            'umax':0,
            'umin': 0,
            'moutput': "auto",
            'ssrduty': 1,
            'ssrpin': 4,
            'relayduty': {'Relay1': 0, 'Relay2': 0, 'Relay3': 0, 'Relay4':0, 'Relay5':0}
            'relaypin': {'Relay1': 0, 'Relay2': 0, 'Relay3': 0, 'Relay4':0, 'Relay5':0}
        }

        #Initialize required variables
        self.output = 0


    # Function to update variables recieved from queue
    def update_variables(self) :
        updated_variables = self.inputqueue.get()
        for variable, value in updated_variables.items():
            self.variabledict[variable] = value

    # Controller output function
    def controller_output(self,duty) :

        #Initialize variables
        relayduty = self.variabledict['relayduty']
        relaypin = self.variabledict['relaypin']
        ssrduty = self.variabledict['ssrduty']
        max_relay_output = 0
        relaystate = {}
        for relay, in relayduty.items() :
            relaystate = {relay:0}
        relayoutput = 0

        # Determine maximum output
        for relay in sorted(relayduty.keys()) :
            max_relay_output += relayduty[relay]
        max_output = self.variabledict['ssrduty'] + max_relay_output

        # Determine current output
        for relay in sorted(relayduty.keys()) :
            relayoutput += relaystate[relay] * relayduty[relay]

        # Determine Required Output
        output = duty * max_output

        # Check  which relays should be switched

        # Relays produce too much output - switch relays off until relays produce less output than the desired output
        if relayoutput > output :
            for relay in sorted(relayduty.keys(), reverse=True) :
                relayoutput -= relaystate[relay] * relayduty[relay]
                relaystate[relay] = 0
                if relayoutput < output : break

        # Relays produce too little output - switch relays on until relays produce just less output than the desired output, so ssr can compensate for the difference
        elif relayoutput + ssrduty  < output :
            for relay in sorted(relayduty.keys()) :
                if relaystate[relay] = 0 :
                    relaystate[relay] = 1
                    relayoutput += relayduty[relay]
                    if relayoutput + ssrduty > output :
                        break

        # If at max duty all should be on
        elif duty = 100 :
            for relay in sorted(relayduty.keys()) :
                relaystate[relay] = 1

        # Calculate PWM duty needed from ssr
        ssroutput = output - relayoutput
        ssr_pwmduty = ssroutput / ssrduty * 100

        #Activate pins to switch relays
        for relay in sorted(relayoutput.keys()):
            GPIO.output(relaypin[relay], relaystate[relay])

        #Change ssr PWM


    # Main looping function of the PID Controller
    def run(self):

        while True:

            # Update control parameters
            k1 = self.variabledict['kp'] + self.variabledict['ki'] + self.variabledict['kd']
            k2 = - self.variabledict['ki'] - 2 * self.variabledict['kd']
            k3 = self.variabledict['kd']
            sp = self.variabledict['setpoint']
            u = self.output

            # Read New Measured Variable
            channel = self.variabledict['input_channel']
            mv = self.adc.Temperature(channel)

            # Update error variables
            e2 = e1
            e1 = e
            e = sp - mv

            delta_u = k1 * e + k2 * e1 + k3 * e2
            u = u + delta_u

            # check for manual mode
            if self.variabledict['moutput'] != "auto" :
                u = self.variabledict['moutput']

            # clamp output to between min and max values
            if u > self.variabledict['umax']:
                u = self.variabledict['umax']
            elif u < self.variabledict['umin']:
                u = self.variabledict['umin']

            duty = u / self.variabledict['umax']
