#! /usr/bin/env python3

import multiprocessing
import queue
import datetime
import time




# PID Controller class
class PIDControllertester(multiprocessing.Process):

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
                '2016-08-12 09:00:00': 20,
                '2016-08-13 09:00:00': 20
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
            'terminate': 0
        }

        # Initialize required variables
        self.setpoint = 0
        self.setpointchanges = 2
        self.output = 0
        self.outputdict = {}

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

    # Main looping function of the PID Controller
    def run(self):

        # Get updated variables from queue
        try:
            while True:
                updated_variables = self.inputqueue.get_nowait()
                for variable, value in updated_variables.items():
                    self.variabledict[variable] = value
                print('initial variables collected - Controller')
        except queue.Empty:
            pass

        mv = 0
        safetytemp = 0
        newumax = 90

        # Main control loop
        while True:

            # Check for updated variables
            try:
                while True:
                    updated_variables = self.inputqueue.get_nowait()
                    print('Collected data from inputqueue - Controller')
                    for variable, value in updated_variables.items():
                        print('new variable at: %s' % variable)
                        self.variabledict[variable] = value
                        # print('new variables collected')
                        # print(self.variabledict)
            except queue.Empty:
                pass

            # Get new setpoint based on current date and time
            self.setpoint_interpolate()

            # generate output
            u = self.output + 9
            if u > 100:
                u = 0

            # generate temp
            mv = mv + 1
            if mv > 100:
                mv = 85

            # generate umax
            newumax += 3
            if newumax > 100:
                newumax -= 10

            # check for manual mode
            if self.variabledict['moutput'] != "auto":
                u = self.variabledict['moutput']

            # clamp output to between min and max values
            if u > self.variabledict['umax']:
                u = self.variabledict['umax']
            elif u < self.variabledict['umin']:
                u = self.variabledict['umin']

            self.output = u
            duty = u / self.variabledict['umax'] * 100

            # Update output dictionary
            self.outputdict['DateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.outputdict['Temperature'] = mv
            self.outputdict['Duty'] = duty
            self.outputdict['Setpoint'] = self.setpoint
            self.outputdict['SafetyTemp'] = safetytemp
            self.outputdict['SafetyTrigger'] = self.safetytrigger
            self.outputdict['Status'] = 'Producing variables'
            self.outputdict['umax'] = newumax

           # Send output to Manager
            self.outputqueue.put(self.outputdict)

            # Check terminate variable
            #print('controller terminate: %s' % self.variabledict['terminate'])
            if self.variabledict['terminate'] == 'True':
                break


            # Wait before running loop again
            time.sleep(self.variabledict['sleeptime'])

        # Ensure GPIO is cleaned up before exiting loop
        print('PID controller exiting')