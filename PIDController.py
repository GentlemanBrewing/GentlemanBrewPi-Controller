#!/usr/bin/python3

# PID controller algorithm
import multiprocessing
import time


# Generate Queue name
def QueueNames :



#pid controller
def PID_Output(inputqueuename,outputqueuename):

    #setup variables
    kp = 0
    ki = 0
    kd = 0
    e = 0
    e1 = 0
    e2 = 0
    umax = 100
    umin = 0
    moutput = "auto"


    # collect variables from queue


    # PID Control Loop
    while (True) :
        k1 = kp + ki + kd
        k2 = -ki - 2 * kd
        k3 = kd

        #update error variables
        e2 = e1
        e1 = e
        e = setpoint - mv

        delta_u = k1 * e + k2 * e1 + k3 * e2
        u = u + delta_u

        # check for manual mode
        if moutput != "auto" :
            u = moutput

        # clamp output to between min and max values
        if u > umax :
            u = umax
        elif u < umin:
            u = umin

        return u

    #


  
  
