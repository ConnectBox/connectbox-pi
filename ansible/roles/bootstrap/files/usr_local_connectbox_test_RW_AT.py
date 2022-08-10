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

dev_i2c = 0x14 # for ATTiny = 0x14
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
print ("\n\nRW_AXP209.py tool instuctions\n")
print ("You can choose to either Read [R] or Write [W] a register in the AXP209")
print ("You will be asked for the register address (in HEX) and, (if doing a")
print ("write) the data to be written (also in HEX).")
print ("Written data will be verified with an automatic read following the write")
print ("and the success or failure will be noted along with the read data.")
print
print ("Typing an S will give a summary of some interesting information.")
print ("Typing an D will give a summary of SD of that interesting information.")
print
print ("Type an X to exit the program.\n\n")

while True:
   global high
   global low
   action = input("Would you like to [R]ead, [W]rite or E[X]it?  ")
   if ((action == "R") or (action == "r")):
      hexreg = input("Enter the register you want to READ (HEX): ")
      hexreg = int(hexreg,16)

      hexval = bus.read_byte_data(dev_i2c, hexreg)
      print ("Value at register %s is %s\n\n" % (format(hexreg, '#02X') , format(hexval, '#02X')))

   elif ((action == "W") or (action == "w")):
      hexreg = input("Enter the register to which you want to WRITE (HEX): ")
      hexreg = int(hexreg,16)
      hexval = input("Enter the value to WRITE (HEX): ")
      hexval = int(hexval,16)
      bus.write_byte_data(dev_i2c, hexreg, hexval)
      newdata = bus.read_byte_data(dev_i2c, hexreg)
      print ("Value at register %s now is %s" % (format(hexreg,'#02X'),format(newdata, '#02X')))
      if newdata == hexval:
         print ("SUCCESS!\n\n")
      else:
         print ("Write did not succeed...\n\n") 
   
   elif ((action == "S") or (action == "s")):
      print ("IPS_OUT voltage reads:     %2.3f V (%s %s)" % (ipsoutVoltage(), format(high,'#02X'), format(low,'#02X')))
      print ("Battery voltage reads:     %2.3f V (%s %s)" % (batteryVoltage(), format(high,'#02X'), format(low,'#02X')))
      print ("Battery charge current:    %2.3f A (%s %s)" % (batteryCharge(), format(high,'#02X'), format(low,'#02X')))
      print ("Battery discharge current: %2.3f A (%s %s)" % (batteryDischarge(), format(high,'#02X'), format(low,'#02X')))
      print ("Chip temperature:           %3.1f C (%s %s)" % (chipTemp(), format(high,'#02X'), format(low,'#02X')))
      print ("Battery Fuel Gauge:         %3.1f %% (%s)" % (batteryFuel(), format(high,'#02X')))
      print

   elif ((action == "L") or (action == 'l')):    #Log battery discharging...
# try some logging...
      print ("Ctrl-z to abort....")
      f = open('log.txt','w')
      f.write('Log of battery discharge\n')
      print('Log of battery discharge\n')
      f.write(tod() + '\n\n')
      f.close()
      while True:
         bv = batteryVoltage()
         bvs = "{:.3f}".format(bv)
         bd = batteryDischarge()
         bds = "{:.3f}".format(bd)
         bf = batteryFuel()
         bfs = "{:.1f}".format(bf)
         f = open('log.txt','a')
         f.write(tod() + ' ' + bvs + 'V ' + bds + 'A ' + bfs + '%\n')
         print(tod() + ' ' + bvs + 'V ' + bds + 'A ' + bfs + '%')
         f.close()
         time.sleep(60)

   elif ((action == "D") or (action == "d")):
      vals1 = []		#empty list
      vals1h = []
      vals1l = []
      vals2 = []		#empty list
      vals2h = []
      vals2l = []
      vals3 = []		#empty list
      vals3h = []
      vals3l = []
      vals4 = []		#empty list
      vals4h = []
      vals4l = []
      vals5 = []		#empty list
      vals5h = []
      vals5l = []
      vals6 = []		#empty list
      vals6h = []
      vals6l = []
      delay = input("Enter the delay between readings (secs)")
      delay = float(delay)
      print
      print ("Time interval between each of 10 readings: %2.1f secs" %delay)
      for x in range(1,11):
         vals1.append(ipsoutVoltage())	
         vals1h.append(high)
         vals1l.append(low)
         vals2.append(batteryVoltage())	
         vals2h.append(high)
         vals2l.append(low)
         vals3.append(batteryCharge())	
         vals3h.append(high)
         vals3l.append(low)
         vals4.append(batteryDischarge())	
         vals4h.append(high)
         vals4l.append(low)
         vals5.append(chipTemp())	
         vals5h.append(high)
         vals5l.append(low)
         vals6.append(batteryFuel())	
         vals6h.append(high)
         vals6l.append(low)
         time.sleep(delay)

      ipsV_sd = sd(vals1)
      batV_sd = sd(vals2)
      batCh_sd = sd(vals3)
      batDc_sd = sd(vals4)
      chTemp_sd = sd(vals5)
      batFuel_sd = sd(vals6)

      ipsV_avg = avg(vals1)
      batV_avg = avg(vals2)
      batCh_avg = avg(vals3)
      batDc_avg = avg(vals4)
      chTemp_avg = avg(vals5)
      batFuel_avg = avg(vals6)

      idx_mx = vals1.index(max(vals1))
      idx_mn = vals1.index(min(vals1))
      maxh = vals1h[idx_mx]
      maxl = vals1l[idx_mx]
      minh = vals1h[idx_mn]
      minl = vals1l[idx_mn]

      print ("ipsoutVoltage avg/sd/max/min/hex:     %2.3f / %2.4f V  (%2.3f / %2.3f  (%s + %s / %s + %s))" %(ipsV_avg, ipsV_sd,vals1[idx_mx], vals1[idx_mn], format(maxh,'#02X'), format(maxl,'#02X'), format(minh,'#02X'), format(minl,'#02X')))

      idx_mx = vals2.index(max(vals2))
      idx_mn = vals2.index(min(vals2))
      maxh = vals2h[idx_mx]
      maxl = vals2l[idx_mx]
      minh = vals2h[idx_mn]
      minl = vals2l[idx_mn]
      print ("Battery Voltage avg/sd/max/min/hex:   %2.3f / %2.4f V  (%2.3f / %2.3f  (%s + %s / %s + %s))" %(batV_avg, batV_sd, vals2[idx_mx], vals2[idx_mn], format(maxh,'#02X'), format(maxl,'#02X'), format(minh,'#02X'), format(minl,'#02X') ))


      idx_mx = vals3.index(max(vals3))
      idx_mn = vals3.index(min(vals3))
      maxh = vals3h[idx_mx]
      maxl = vals3l[idx_mx]
      minh = vals3h[idx_mn]
      minl = vals3l[idx_mn]
      print ("Battery Charge avg/sd/max/min/hex:    %2.3f / %2.4f A  (%2.3f / %2.3f  (%s + %s / %s + %s))" %(batCh_avg, batCh_sd, vals3[idx_mx], vals3[idx_mn], format(maxh,'#02X'), format(maxl,'#02X'), format(minh,'#02X'), format(minl,'#02X')))


      idx_mx = vals4.index(max(vals4))
      idx_mn = vals4.index(min(vals4))
      maxh = vals4h[idx_mx]
      maxl = vals4l[idx_mx]
      minh = vals4h[idx_mn]
      minl = vals4l[idx_mn]
      print ("Battery Discharge avg/sd/max/min/hex: %2.3f / %2.4f A  (%2.3f / %2.3f  (%s + %s / %s + %s))" %(batDc_avg, batDc_sd, vals4[idx_mx], vals4[idx_mn], format(maxh,'#02X'), format(maxl,'#02X'), format(minh,'#02X'), format(minl,'#02X')))


      idx_mx = vals5.index(max(vals5))
      idx_mn = vals5.index(min(vals5))
      maxh = vals5h[idx_mx]
      maxl = vals5l[idx_mx]
      minh = vals5h[idx_mn]
      minl = vals5l[idx_mn]
      print ("Chip Temperature avg/sd/max/min/hex:   %3.1f / %2.4f C  ( %3.1f / %3.1f   (%s + %s / %s + %s))" %(chTemp_avg, chTemp_sd, vals5[idx_mx], vals5[idx_mn], format(maxh,'#02X'), format(maxl,'#02X'), format(minh,'#02X'), format(minl,'#02X')))


      idx_mx = vals6.index(max(vals6))
      idx_mn = vals6.index(min(vals6))
      maxh = vals6h[idx_mx]
      minh = vals6h[idx_mn]
      print ("Fuel Gauge avg/sd/max/min/hex:         %3.1f / %2.3f  %%  ( %3.1f / %3.1f   (%s / %s))" %(batFuel_avg, batFuel_sd, vals6[idx_mx], vals6[idx_mn], format(maxh,'#02X'), format(minh,'#02X')))

      print

   elif ((action == "X") or (action == "x")):
      break

   

