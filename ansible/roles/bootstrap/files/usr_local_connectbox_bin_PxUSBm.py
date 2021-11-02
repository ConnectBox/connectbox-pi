#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
PxUSBm.py
   (Partition Expansion USB mount)

This module is a marriage of code to do partition expansion during the first power on (formerly expandFS.py)
 and code to monitor USB activity to mount and unmount USB sticks as they are added and removed from
 USB ports on the ConnectBox. (Testing has shown problems with using two python scripts in the rc.local file.) 
'''

# Python code to expand filesystem

'''
General outline of Partition Expansion need:

The building of an image results in a single partition which is much smaller than the size of the uSD card
(typically 2 - 3 GB). It is desired that this partition be expanded to the full size of the uSD card on 
which the image is placed. To do this, we will use the fdisk program to find the starting sector of the 
partition. If we then delete the partition, followed by the creation of a new primary partion we can set 
the start of the new partition at the starting sector of the old partition, and then set the size of the 
new partition to be the remainder of the disk. During this process, two reboots will be required, one after
setting up the new partition with fdisk and one after doing the file expansion using resize2fs. 

Method:

We will use the library pexpect to handle the interactions between this program and the fdisk program and 
the library re to handle the regex calls to sort out the number of the starting sector. We also need to 
handle the selection of whether we are in the fdisk section of the process or the resize2fs section. To do
this, we will use a second file, expand_progress.txt. Initially, that file will not exist. Upon the first
boot of the uSD with a new image, this code will be called (rc.local). At the top of this code, we will
look for the expand_progress.txt file. If it doesn't exist, we know that we are in the fdisk section, and
so that section will be run. If it completes successfully, the expand_progress file will be created 
"fdisk_done" will be written and a reboot will be issued by this code. At reboot, this file will be 
called and again, will test for the existence of expand_progress.txt. Upon finding the file, it will 
read the contents ("fdisk_done") and if "fdisk_done" is the only entry,
will proceed to run the resize2fs section of the code. Upon successful completion of that section,
the expand_progress.txt file will be opened an written with "resize2fs_done" and a second reboot invoked. After
this reboot, this code will look for the expand_progress.txt file, find it present (fdisk stuff done), 
read the contents (not empty, so resize2fs complete) and exit. Thus at each reboot from that point on, 
this code will quickly test the expand_progress.txt file an finding the process complete, will exit.

'''

import pexpect
import time
import re
import os

# globals for Partion expansion
progress_file = '/usr/local/connectbox/bin/expand_progress.txt'

# globals for USB monitoring
DEBUG = 0
global total
total = 0
c=["","",""]
loc=[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
# mnt[x]>=0 where x is the usb port of the mount and mnt[x] is the line of the /dev/sdx1
global mnt
mnt=[-1,-1,-1,-1,-1,-1,-1,-1,-1, -1, -1]
d=["","","","","","","","","","","","","","","","","","","","","",""]

def mountCheck():
    global mnt
    global total
    j = 0                   #mount iterator looking for unmounted devices
    b = os.popen('lsblk').read()
    while (j < total):
      if DEBUG: print("loop 1, iterate",j)
      if (mnt[j] >= 0):
        if not ('usb' + chr(ord('0')+j) in b):
          c = "umount /media/usb" + chr(ord('0')+j)
          res = os.system(c)
          if DEBUG: print("completed unmount /media/usb", chr(ord('0')+j))
          if not res:
            mnt[j] = -1
            if j>0:
               os.popen('rmdir /media/usb'+chr(ord('0')+j))
            j += 1
          else:
            if DEBUG: print("Failed to " + c)
            mnt[j] = -1
            j += 1
        else:
          #Were here with the device still mounted
          j += 1
      else:
        #were here because there was no mount device detected
        if DEBUG: print("device not mounted usb", j)
        j += 1
    i=0                       #line iterator
    j=0                       #used for finding sdx1's
    k=0                       #used for usb mounts
    loc=[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
    b = os.popen('lsblk').read()
    c = b.partition("\n")
# while we have lines to parse we check each line for an sdx1 device and mount it if not already
    while ((c[0] != "") and (i<10)):
      if DEBUG: print("Loop 2, iterate:",i, c[0])
      d[i] = c[0]
      e=re.search('sd[a-z]1', d[i])
      if e: 
        loc[j]=i
        if not (('usb' in d[i]) or ('part /' in d[i])):     #True if were not mounted but should be
          while (k < 10) and (mnt[k] >= 0):                 #Find an empty usbX to mount to
            if DEBUG: print("loop 3, iterate:",k)
            k += 1
          if not (os.path.exists("/media/usb"+chr(ord("0")+k))):  #if the /mount/usbx isn't there create it
            res = os.system("mkdir /media/usb"+chr(ord("0")+k))
          b = "mount /dev/" + e.group() + " /media/usb" + chr(ord('0')+k)+ " -o noatime,nodev,nosuid,sync,iocharset=utf8"
          res = os.system(b)
          if DEBUG: print("completed mount /dev/",e.group)
          mnt[k]=i
          k += 1
          j += 1
        else:
          if ('usb' in d[i]):
            a = d[i].partition("usb")
            if (a[2] != "") and (a[2].isalnum()):
              l = ord(a[2])-ord("0")
              mnt[l]=i
              j+=1
              if DEBUG: print("/dev/sdx1 is already mounted as usb",chr(l+ord('0')))
            else:
              if DEBUG: print("Error parsing usb# in line", i)
              j+= 1
          else:
              if DEBUG: print("/dev/sdx1 is already mounted but not as usb", d[i])
              j+= 1
      c = c[2].partition("\n")
      i += 1
# now that we have looked at all lines in the current lsblk we need to count up the mounts
    j = -1
    i = 0
    while (i < 10):            # we will check a maximum of 10 mounts
      if DEBUG: print("loop 4, iterate:",i)
      if (mnt[i] != -1):
        i +=1
        j +=1
      else:                   # we have a hole or are done but need to validate
        k = i+1
        while (k < 10) and (mnt[i] == -1):  #checking next mount to see if it is valid
          if DEBUG: print("loop 5, iterate:",k,i)
          if (mnt[k] != -1):
            mnt[i] = mnt[k]   # move the mount into this hole and clear the other point
            j += 1
            mnt[k] = -1
            i += 1
            k += 1
            if DEBUG: print("had to move mount to new location",k," from ",i)
          else:     # we have no mount here
            k += 1
        if (k == 10):           # if we have look at all mounts then were done otherwise we will check again
          i=10
    total = j+1
    if DEBUG: print("total of devices mounted is", total)
    if DEBUG: print("located", mnt)
    return()



def do_resize2fs():
	# find the filesystem name ... like "/dev/mmcblk0p1"
    out = pexpect.run('df -h')
    p = re.compile('/dev/mmcblk[0-9]p[0-9]+')
    out = out.decode('utf-8') 
    m = p.search(out)
    FS = m.group()
    
    # we have the FS string, so build the command and run it
    cmd = 'resize2fs ' + FS
    out = pexpect.run(cmd, timeout=600)  # 10 minutes should be enough for the resize
    out = out.decode('utf-8')
    if "blocks long" in out:
        print("resize2fs complete... now reboot")
        f = open(progress_file, "w")
        f.write("resize2fs_done")
        f.close()
        os.system('reboot')
        

def do_fdisk():

    child = pexpect.spawn('fdisk /dev/mmcblk0', timeout = 10)
    try:
	    i = child.expect(['Command (m for help)*', 'No such file or directory']) # the match is looking for the LAST thing that came up so we need the *
    except:
	    print("Exception thrown")
	    print("debug info:")
	    print (str(child))

	# the value of i is the reference to which of the [] arguments was found
    if i==1:
        print("There is no /dev/mmcblk0 partition... exiting")
        child.kill(0)
    if i==0:
        print("Found it!")	
	# continuing

	# "p" get partition info and search out the starting sector of mmcblk0p1
    child.sendline('p')
    i = child.expect('Command (m for help)*')  
	# the child.before contains all that came BEFORE we found the expected text
	#print (child.before)  
    response = child.before

	# change from binary to string
    respString = response.decode('utf-8')
	
    p = re.compile('mmcblk[0-9]p[0-9]\s*[0-9]+')		# create a regexp to get close to the sector info
    m = p.search(respString)		# should find "mmcblk0p1   8192" or similar, saving as object m
    match = m.group()				# get the text of the find
    p = re.compile('\s[0-9]+')		# a new regex to find just the number from the match above
    m = p.search(match)
    startSector = m.group()
    print("starting sector = ", startSector )

	# "d" for delete the partition
    child.sendline('d')
    i = child.expect('Command (m for help)*')  
#	print("after delete ",child.before)

	# "n" for new partition
    child.sendline('n')
    i = child.expect('(default p):*')
#	print("after new ",child.before)

	# "p" for primary partition
    child.sendline('p')
    i = child.expect('default 1*')
#	print ("after p ", child.before)

	# "1" for partition number 1
    child.sendline('1')
    i = child.expect('default 2048*')
#	print (child.before)

	# send the startSector number
    child.sendline(startSector)
    child.expect('Last sector*')
#	print("At last sector... the after is: ", child.after)

	# take default for last sector
    child.sendline('')
    i = child.expect('signature*')

	# "N" don't remove the signature
    child.sendline('N')
    i = child.expect('Command (m for help)*')  

	# "w" for write and exit
    child.sendline('w')
    i = child.expect('Syncing disks*')  

    print("exiting the fdisk program... now reboot")
    f = open(progress_file, "w")
    f.write("fdisk_done")
    f.close()
    os.system('reboot')


if __name__ == "__main__":
# First handle the partition expansion

    # Sort out how far we are in the partition expansion process
    file_exists = os.path.exists(progress_file)
    if file_exists == False:
        do_fdisk()             # this ends in reboot() so won't return

    else: 
        f = open(progress_file, "r")
        progress = f.read()
        f.close()
        if "resize2fs_done" not in progress:
            do_resize2fs()     # this ends in reboot() so won't return

# Once partition expansion is complete, handle the ongoing monitor of USBs

    while True:
        loop_time = 3
        mountCheck()
        time.sleep(loop_time)
