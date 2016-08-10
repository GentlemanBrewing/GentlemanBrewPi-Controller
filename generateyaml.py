#!/usr/bin/env python3

import yaml

variabledict = {
            'sleeptime': 5,
            'kp': 0,
            'ki': 0,
            'kd': 0,
            'setpoint': 0,
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

processdict = {'inputqueue': 0,
               'outputqueue': 0
               }

totaldict = {'process_data': processdict,
             'process_variables': variabledict
             }


f = open('Confignew.yaml', "w")
yaml.dump(totaldict, f)
f.close