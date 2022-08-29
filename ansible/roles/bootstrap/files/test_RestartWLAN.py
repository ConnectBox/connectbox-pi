import pexpect
import time
import logging
import re
import os
from subprocess import Popen, PIPE
import subprocess

def RestartWLAN(b):
  print("In RestartWLAN()")
  wlanx = "wlan"+str(b)
  print ("wlanx->"+wlanx)

  cmd = "systemctl restart hostapd"
  rv = subprocess.call(cmd, shell=True)
  print("hostapd... Returned value ->", rv)

  cmd = "systemctl restart dnsmasq"
  rv = subprocess.call(cmd, shell=True)
  print("dmasq... Returned value ->", rv)

  cmd = "ifdown "+wlanx
  rv = subprocess.call(cmd, shell=True)
  print("ifdown ... Returned value ->", rv)

  cmd = "ifup "+wlanx
  rv = subprocess.call(cmd, shell=True)
  print("ifup... Returned value ->", rv)
  print("..")

  time.sleep(3)

  cmd = "iwconfig"
  rv = subprocess.check_output(cmd)
  rvs = rv.decode("utf-8")
  print("iwconfig Returned value ->", rvs)
  print("..")
  print(rvs)
 
  if ("802.11gn" in rvs):
    print ("WLAN IS UP!")
  else:
    print("WLAN not up... we need to run hostapd")
    cmd = "systemctl restart hostapd"
    rv = subprocess.call(cmd, shell=True)
    print("hostpad... Returned value ->", rv)
     

  exit()



if __name__ == "__main__":
  RestartWLAN(0)

