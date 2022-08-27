#! /usr/bin/env python3
import smbus2
import os
from axp209 import AXP209, AXP209_ADDRESS

try:
  axp = AXP209(10)                            # i2c-10 on CM4 
  hexval = axp.bus.read_byte_data(0x14,0x10)  # ATTiny there?
  hexval = axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
  hexval = hexval | 0x80
  print (hexval)
  axp.bus.write_byte_data(AXP209_ADDRESS,0x32,hexval)
except:
  os.system("shutdown now")
