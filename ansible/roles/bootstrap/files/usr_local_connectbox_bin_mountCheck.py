# Loop to test for insertion of USB stick and to mount it as /media/usb0
#  Also tests for removal of USB and responds with umount /media/usb0

import os
import time

usbMounted = False

def mountCheck():
    global usbMounted
    b = os.popen('lsblk').read()
    if 'sda1' in b:
        if usbMounted == True:
            return
        res = os.system("mount /dev/sda1 /media/usb0")
        if res == 0:
            usbMounted = True
    else:
        if (usbMounted == False):
            return
        os.system("umount /media/usb0")
        usbMounted = False

if __name__ == '__main__':
    while True:
        loop_time = 3
        mountCheck()
        time.sleep(loop_time)
        