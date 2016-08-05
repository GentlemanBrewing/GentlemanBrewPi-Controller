#!/usr/bin/python3
# Convert Voltage from ADC to Temperature Reading

from ABE_ADCPi import ADCPi
from ABE_Helpers import ABEHelpers
import time
import os

i2c_helper = ABEHelpers()
bus = i2c_helper.get_smbus()
adc = ADCPi(bus, 0x68, 0x69, 16)

class ADCTEMP:


  #Initialize Variables
  __R1 = 0
  __R2 = 0
  __R3 = 0
  __Rx = 0.0
  __Vin = 0.0
  
  def __init__(self, R1=3300, R2=100, R3=3300, Vin=3.3):
    self.__R1 = R1
    self.__R2 = R2
    self.__R3 = R3
    self.__Vin = Vin
    adc.set_pga(8)
  
  def Resistance(self, channel):
    Vb = adc.read_voltage(channel)
    # Input variables
    R1 = self.__R1
    R2 = self.__R2
    R3 = self.__R3
    Vin = self.__Vin
    # Wheatstone bridge calculation
    Rx = (R2 * R3 + R3 * (R1 + R2) * (Vb / Vin)) / (R1 - (R1 + R2) * (Vb / Vin))
    return Rx

  # Calculate Temperature for PT100  
  def Temperature(self, channel):
    resistance = self.Resistance(channel)
    t = ((resistance - 100) / 38.51 ) * 100
    return float(t)

