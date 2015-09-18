#!/usr/bin/python3
# Convert Voltage from ADC to Temperature Reading

from ABE_ADCPi import ADCPi
from ABE_helpers import ABEHelpers
import time
import os

i2c_helper = ABEHelpers()
bus = i2c_helper.get_smbus()
adc = ADCPi(bus, 0x68, 0x69, 12)


def Voltage(channel)
  voltage = adc.readvoltage(channel)
  return voltage
  
def Resistance(voltage)
  resistance = (R2 * R3 + R3 * (R1 + R2) * (Vb / Vin)) / (R1 - (R1 + R2) * (Vb / Vin))
  return resistance
  
  
