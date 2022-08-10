#!/usr/bin/python

# Nice summary of smbus commands at: 
#    http://wiki.erazor-zone.de/wiki:linux:python:smbus:doc
#
# Need the following before using commands...
import smbus2
import time
import datetime
import math

# Then need to create a smbus object like...
bus = smbus2.SMBus(10)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

# Then we can use smbus commands like... (prefix commands with "bus.") 
#
# read_byte(dev)     / reads a byte from specified device
# write_byte(dev,val)   / writes value val to device dev, current register
# read_byte_data(dev,reg) / reads byte from device dev, register reg
# write_byte_data(dev,reg,val) / write byte val to device dev, register reg 
#


# some time of day functions...
def tod():
   ts = time.time()
   st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
   return (st)


# Start building the interactive menuing...

dev_i2c = 0x34 # for AXP209 = 0x34
global high 
global low 

# calculate std dev of list
def avg(list):
   sum = 0
   for num in list:
      sum = sum + num
   avg = sum / len (list)
   return (avg)

def sd(list):
   a = avg (list)
   sum2 = 0
   for num in list:
      diff2 = (num - a) * (num - a)
      sum2 = sum2 + diff2
   avg2 = sum2/float (len(list))
   sd = math.sqrt(avg2)
   return(sd)

def batteryVoltage():
   global high
   global low
   datH = bus.read_byte_data(dev_i2c,0x78)
   time.sleep (0.01)
   datL = bus.read_byte_data(dev_i2c,0x79)
   time.sleep (0.01)
   high = datH
   low = datL
   dat = datH * 16 + datL
   return (dat * 0.0011)

def batteryCharge():
   global high
   global low
   datH = bus.read_byte_data(dev_i2c,0x7A)
   time.sleep(0.01)
   datL = bus.read_byte_data(dev_i2c,0x7B)
   time.sleep(0.01)
   high = datH
   low = datL
   dat = datH * 16 +datL
   return (dat * 0.0005)

def batteryDischarge():
   global high
   global low
   bus.write_byte_data(dev_i2c,0x82,0xC3)
   time.sleep(0.01)
   datH = bus.read_byte_data(dev_i2c,0x7C)
   time.sleep(0.01)
   datL = bus.read_byte_data(dev_i2c,0x7D)
   time.sleep(0.01)
   high = datH
   low = datL
   dat = datH * 32 + datL
   return (dat * 0.0005)

def ipsoutVoltage():
   global high
   global low
   datH = bus.read_byte_data(dev_i2c,0x7E)
   time.sleep(0.01)
   datL = bus.read_byte_data(dev_i2c,0x7f)
   time.sleep(0.01)
   high = datH
   low = datL
   dat = datH * 16 + datL
   return (dat * 0.0011)

def chipTemp():
   global high
   global low
   datH = bus.read_byte_data(dev_i2c,0x5E)
   time.sleep(0.01)
   datL = bus.read_byte_data(dev_i2c,0x5F)
   time.sleep(0.01)
   high = datH
   low = datL
   dat = datH * 16 + datL
   return (dat * 0.1 - 144.7)

def batteryFuel():
   global high
   high = bus.read_byte_data(dev_i2c,0xB9)
   return high

#
# Give some instructions:
print ("Beginning Battery Logging.\n\n")

while True:
   global high
   global low
   
   print ("Ctrl-z to abort....")
   f = open('log.txt','w')
   f.write('Log of battery discharge\n')
   print('Log of battery discharge\n')
   f.write(tod() + '\n\n')
   f.close()
   start_time = time.time()
   while True:
      bv = batteryVoltage()
      bvs = "{:.3f}".format(bv)
      bd = batteryDischarge()
      bds = "{:.3f}".format(bd)
      bf = batteryFuel()
      bfs = "{:.1f}".format(bf)
      f = open('log.txt','a')
      f.write(tod() + ' ' + bvs + 'V ' + bds + 'A ' + bfs + '%\n')
#      print(tod() + ' ' + bvs + 'V ' + bds + 'A ' + bfs + '%')
      f.close()
      time.sleep(60.0 - ((time.time() -start_time) %60.0)) # exactly 60 sec between readings
   
