#!/usr/bin/python3

import RPi.GPIO as GPIO
import time


gpiopins = {'4': 'GPIO.OUT',
            '17': 'GPIO.OUT',
            '27': 'GPIO.OUT',
            '22': 'GPIO.OUT',
            '10': 'GPIO.OUT',
            '9': 'GPIO.OUT',
            '11': 'GPIO.OUT',
            '5': 'GPIO.OUT',
            '6': 'GPIO.IN',
            '14': 'GPIO.OUT',
            '15': 'GPIO.OUT',
            '18': 'GPIO.OUT',
            '23': 'GPIO.OUT',
            '24': 'GPIO.OUT',
            '25': 'GPIO.OUT',
            '8': 'GPIO.OUT',
            '7': 'GPIO.OUT',
            '12': 'GPIO.OUT'}

GPIO.setmode(GPIO.BCM)

for pin, mode in gpiopins.items():
    pinnum = int(pin)
    print(pinnum)
    print(mode)
    GPIO.setup(pinnum, GPIO.OUT)
time.sleep(1)


for pin, mode in gpiopins.items():
    #if gpiopins[pin] == 'GPIO.OUT':
        pinnum = int(pin)
        print(gpiopins[pin])
        print("setting pin %r high" % pinnum)
        #GPIO.output(pinnum, 1)
        time.sleep(5)
        #GPIO.output(pin, 0)

GPIO.cleanup()
