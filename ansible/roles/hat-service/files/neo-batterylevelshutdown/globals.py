# -*- coding: utf-8 -*-
# globals.py
#
# Here we have a single place to create and make available globals which
#  will be used in multiple modules

# To easily create brand.j2, use the tool BrandCreationTool.py

import io
import os
import json
import logging
import time

# need to initialize the variables outside of the init() function
# Then the init() will fill in the correct values

device_type = "PH_type"
brand_name = "PH_name"
logo_image = "PH_image"
splash_x = 7
splash_y = 0
splash_font = 26
enable_mass_storage = ""        # additive to the g_device paramater
screen_enable = [1,1,1,1,1,1,1,1,1,1,1,1,1,1]

# font sizes are just specified here
font30 = 26
font20 = 19
font14 = 13
font10 = 11
g_device = "g_serial"           # blank for no g_device on OTG
port = 0
otg = "0"                       # 'none', 0 for normal positive OTG mode, 1 for inverted OTG mode
usbnomount = 0                  # enables and dissables auto mount.
timestamp = ""
clientIF = ""
sequence_time = 0.0
sequence = 0.0
a = ""



from . import page_battery
from .HAT_Utilities import get_device



def init():
  # by defining as global, the following variables can be modified
  #  by the init() function

    global device_type
    global brand_name
    global logo_image
    global splash_x
    global splash_y
    global splash_font
    global usbnomount
    global screen_enable
    global enable_mass_storage      # mass storage enabled overrides g_device always but is subject to otg setting
    global g_device                 # g_device is subject to otg setting
    global otg                      # high, low, none, both
    global port
    global timestamp
    global clientIF
    global sequence                 #Used for rotation of waiting symbol
    global sequence_time
    global a                        #Display value on screen

 

    logging.debug("Initializing Globals")

  # Using a dictionary and json to store Branding stuff
  # Read the dictionary
    f = open('/usr/local/connectbox/brand.j2', "r")
    data = f.read()
    f.close()
    js = json.loads(data)
    timestamp = os.path.getmtime('/usr/local/connectbox/brand.j2')
    if (sequence >7) or (sequence < 0): sequence = 0
    sequence_time = time.time()

# May want to put some checks in to allow fields to be missing and
#  if so, revert to defaults...

    brand_name = js["Brand"]
    logo_image = js["Image"]
    splash_font = js["Font"]
    splash_x = js["pos_x"]
    splash_y = js["pos_y"]

    # Just in case our brand.j2 doesn't have these parameters...
    #   (for any that are missing, just keep the defaults)
    try:
        device_type = js["Device_type"]
    except:
        pass

    try:
        usbnomount = js["usb0NoMount"]
    except:
        pass
    try:
        screen_enable = [
            js['lcd_pages_main'],
            js['lcd_pages_info'],
            js['lcd_pages_battery'],
            js['lcd_pages_multi_bat'],
            js['lcd_pages_memory'],
            js['lcd_pages_stats_hour_one'],
            js['lcd_pages_stats_hour_two'],
            js['lcd_pages_stats_day_one'],
            js['lcd_pages_stats_day_two'],
            js['lcd_pages_stats_week_one'],
            js['lcd_pages_stats_week_two'],
            js['lcd_pages_stats_month_one'],
            js['lcd_pages_stats_month_two'],
            js['lcd_pages_admin'],
        ]
    except:
        pass

    try:
        otg = js["otg"]
    except:
        pass
    try:
        g_device = js["g_device"]
    except:
        pass
    try:
        enable_mass_storage = js["Enable_MassStorage"]
    except:
        pass

    logging.debug("globals screen_enable="+str(screen_enable))

# check that the brand name eg: hostname hasn't changed.
# if it did we need to update the brand and the hostname
    f = open("/etc/hostname", mode="r", encoding="utf-8")
    bname = f.read().rstrip()
    f.close()
    if (bname.lower() != brand_name.lower()):
        brand_name = bname
        js["Brand"] = bname
        f = open("/usr/local/connectbox/brand.j2", 'w')
        f.write(json.dumps(js))
        f.close()


  #find and set device_type global
    device_type = "NEO"
    f = open("/proc/cpuinfo", mode="r", encoding = 'utf-8')
    filx = f.read()

    if ("Raspberry" in filx):
        if ("Compute Module" in filx):
            device_type = "CM"
            port = 10
        else:           #all other Raspberry Pi version other than compute modules
            device_type = "PI"
            port = 1
    if ("Radxa CM3" in filx):
        device_type = "RM3"
        port = 0               # i2c port 

# Read the default AccessPoint Interface for the front panel display
# note this will get re-read occassionally
    f.close()

    f = open("/usr/local/connectbox/wificonf.txt","r")
    dat = f.read()
    f.close()
    clientIF = dat.split("\n")[0].partition("AccessPointIF=")[2]
