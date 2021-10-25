#!/usr/bin/env Python3
# -*- coding: utf-8 -*-
# Loop to test for insertion of USB stick and to mount it as /media/usb0
#  Also tests for removal of USB and responds with umount /media/usb0

import os
import time

usbMounteda = False
usbMountedb = False

def mountCheck():
    global usbMounteda
    global usbMountedb
    b = os.popen('lsblk').read()
    if 'sda1' in b:
        if usbMounteda == True:
            return
        res = os.system("mount /dev/sda1 /media/usb0 -o iocharset=utf8")
        if res == 0:
            usbMounteda = True
    else:
        if (usbMounteda == False):
            return
        os.system("umount /media/usb0")
        usbMounteda = False

    if 'sdb1' in b:
        if usbMounteda == True:
            return
        if usbMountedb == True:
            return
        res = os.system("mount /dev/sdb1 /media/usb0 -o iocharset=utf8")
        if res == 0:
            usbMountedb = True
    else:
        if (usbMountedb == False):
            return
        os.system("umount /media/usb0")
        usbMountedb = False

if __name__ == '__main__':
    while True:
        loop_time = 3
        mountCheck()
        time.sleep(loop_time)
        