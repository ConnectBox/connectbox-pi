#!/usr/bin/env Python3
# -*- coding: utf-8 -*-
# Loop to test for insertion of USB stick and to mount it as /media/usb0
#  Also tests for removal of USB and responds with umount /media/usb0

import os
import time

global total
c=["","",""]
loc=[-1,-1,-1,-1,-1,-1,-1,-1,-1]
mnt=[-1,-1,-1,-1,-1,-1,-1,-1,-1]
d=["","","","","","","","","","",""]

def mountCheck():
    global mnt
    i=0
    j=0
    b = os.popen('lsblk').read()
    c = b.partition("\n")
    while ((c[2] != "") and (i<10)):
      d[i] = c[0]
      a = 'sd'+chr(ord("a")+j)+"1"
      if a in d[i]:
        loc[j]=i
        j += 1 
      c = c[2].partition("\n")
      i += 1
    d[i] = c[0]
    a = 'sd'+chr(ord("a")+j)+"1"
    if a in d[i]:
      loc[j]=i
      j += 1 
    total = j
    i = 0 
    j = 0
    while (i <= total):
      if (mnt[i] < 0) and (loc[i] > 0):
        c = d[i].partition("part")
        if c[2] == " ":
          a = 'sd'+chr(ord("a")+i)+"1"
          b = "mount /dev/" + a + " /media/usb" + chr(j) + " -o iochrset=utf8"
          res = os.system(b)
          if res == 0:
             mnt[i] = j
             j += 1
        else:
          if (mnt[i] >= 0):
            b = "umount /media/usb" + chr(mnt[i])
            os.system(b)
            mnt[i] = -1


if __name__ == '__main__':
    while True:
        loop_time = 3
        mountCheck()
        time.sleep(loop_time)
        