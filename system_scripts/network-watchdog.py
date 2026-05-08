#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import subprocess
import json
import logging
import logging.handlers
import re



def get_AP():
    try:
        f = open("/usr/local/connectbox/wificonf.txt", "r")
        wifi = f.read()
        f.close()
        apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
        AP = int(apwifi.split("wlan")[1])
        return AP
    except:
        return 0

def check_iwconfig(b):
    wlanx = "wlan"+str(b)
    try:
        cmd = "iwconfig"
        rv = subprocess.check_output(cmd, shell=True)
        rvs = rv.decode("utf-8").split(wlanx)
        if (len(rvs) >= 2):
            wlanx_flags = str(rvs[1]).find("Mode:Master")
            if (wlanx_flags) >= 1:
                return True
    except:
        pass
    return False

def check_network():
    AP = get_AP()
    AP_up = check_iwconfig(AP)
    if not AP_up:
        print("AP down, attempting restart")
        try:
            os.system(f"ifdown wlan{AP}")
            os.system(f"ifup wlan{AP}")
        except:
            pass
        
        if not check_iwconfig(AP):
            os.system("/bin/systemctl restart hostapd")
            if not check_iwconfig(AP):
                print("Still not up, attempting to reload driver")
                driver = None
                try:
                    res = os.popen("lshw -c Network").read()
                    r = res.split("wlan")
                    for i in range(1, len(r)):
                        if len(r[i]) > 0 and r[i][0] == str(AP):
                            if "driver=" in r[i]:
                                driver = r[i].split("driver=")[1].split(" ")[0]
                                break
                except:
                    pass
                
                if driver and driver != "none":
                    os.system("rmmod " + driver)
                    time.sleep(2)
                    os.system("modprobe " + driver)
                else:
                    os.system("rmmod 8812au 2>/dev/null; rmmod 8189fs 2>/dev/null; rmmod brcmfmac 2>/dev/null")
                    time.sleep(2)
                    os.system("modprobe 8812au 2>/dev/null; modprobe 8189fs 2>/dev/null; modprobe brcmfmac 2>/dev/null")
                
                time.sleep(5)
                os.system(f"ifup wlan{AP}")
                os.system("/bin/systemctl restart hostapd")

if __name__ == "__main__":
    print("Network watchdog started.")
    # Give the system time to boot
    time.sleep(30)
    while True:
        check_network()
        time.sleep(30)
