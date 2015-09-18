#!/usr/bin/python3
# Convert Voltage from ADC to Temperature Reading

from ABE_ADCPi import ADCPi
from ABE_helpers import ABEHelpers
import time
import os

i2c_helper = ABEHelpers()
bus = i2c_helper.get_smbus()
adc = ADCPi(bus, 0x68, 0x69, 16)

  
def Resistance(self, channel)
  # Default Resistance values in wheatstone bridge
  R1 = 3300
  R2 = 100
  R3 = 3300
  Vin = 3.3
  Vb = adc.read_voltage(channel)
  # Wheatstone bridge calculation
  Rx = (R2 * R3 + R3 * (R1 + R2) * (Vb / Vin)) / (R1 - (R1 + R2) * (Vb / Vin))
  return Rx
  
def Temperature(self, channel)
  resistance = self.Resistance(channel)
  t = (resistance - 100) / 38.51 ) * 100
  return t
