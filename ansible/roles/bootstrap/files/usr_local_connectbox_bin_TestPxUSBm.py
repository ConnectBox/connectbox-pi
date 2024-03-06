#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
PxUSBm.py test for running
   (Partition Expansion USB mount)

This module is a check of code to do veryify that PxUSBm is running.  If it is not it is restarted, or attempted to be restarted.
If successfull then it is happy if not unhappy
'''


import pexpect
import time
import logging
import re
import os
from subprocess import Popen, PIPE
import subprocess
import io
import json
import sys

def runcheck():
    process = Popen(["/bin/systemctl",'status','PxUSBm'], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    if x < 0:									#we found our AP ifup service
        print("Ok we found the PxUSBm.service not running")
        logging.info("Ok we found an PxUSBm.service not running")
        try:
            print("Ok were going to try restarting the PxUSBm.service")
            logging.info("OK we are going to try restarting the PxUSBm.service")
            os.system("/bin/systemctl restart PxUSBm")
            time.sleep(20)
            process = Popen(["/bin/systemctl","status","PxUSBm"], shell=False, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            serva == str(stdout)
            x = serva.find("Active: active")
            if x > 0:
                print("Well we succeeded in restarting the PxUSBm service")
                logging.info("Well we succeded in restarting the PxUSBm.service")
                return(0)								#Ok we succeeded in the restart were up and running.
            else:
                logging.info("We didn't succeed on the restart its still down")
                print("Well we didn't succeed on the restart of PxUSBm its still down")
                return(1)
        except:
           logging.info("We failed on the restart attempt of PxUSBm.service")
           print("We failed on the restart attempt of PxUSBm.service")
           return(1)								#We errored out on the retry of starting the ifup@AP service
    else:
        print("PxUSBm is running")
        return(0)


if __name__ == "__main__":

    runcheck()

