
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


#General outline of Partition Expansion need:

#The building of an image results in a single partition which is much smaller than the size of the uSD card
#(typically 2 - 3 GB). It is desired that this partition be expanded to the full size of the uSD card on
#which the image is placed. To do this, we will use the fdisk program to find the starting sector of the
#partition. If we then delete the partition, followed by the creation of a new primary partion we can set
#the start of the new partition at the starting sector of the old partition, and then set the size of the
#new partition to be the remainder of the disk. During this process, two reboots will be required, one after
#setting up the new partition with fdisk and one after doing the file expansion using resize2fs.

#Method:

#We will use the library pexpect to handle the interactions between this program and the fdisk program and
#the library re to handle the regex calls to sort out the number of the starting sector. We also need to
#handle the selection of whether we are in the fdisk section of the process or the resize2fs section. To do
#this, we will use a second file, expand_progress.txt. Initially, that file will not exist. Upon the first
#boot of the uSD with a new image, this code will be called (rc.local). At the top of this code, we will
#look for the expand_progress.txt file. If it doesn't exist, we know that we are in the fdisk section, and
#so that section will be run. If it completes successfully, the expand_progress file will be created
#"fdisk_done" will be written and a reboot will be issued by this code. At reboot, this file will be
#called and again, will test for the existence of expand_progress.txt. Upon finding the file, it will
#read the contents ("fdisk_done") and if "fdisk_done" is the only entry,
#will proceed to run the resize2fs section of the code. Upon successful completion of that section,
#the expand_progress.txt file will be opened an written with "resize2fs_done" and a second reboot invoked. After
#this reboot, this code will look for the expand_progress.txt file, find it present (fdisk stuff done,
#read the contents (not empty, so resize2fs complete) and exit. Thus at each reboot from that point on,
#this code will quickly test the expand_progress.txt file an finding the process complete, will exit.


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

# globals for Partion expansion
progress_file = '/usr/local/connectbox/expand_progress.txt'

# globals for USB monitoring
global DEBUG		#Debug 1 for netowrking, 2 for summary of mounts, 3 for detail of mounts

global total
total = 0
c=["","",""]

global loc
loc=[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]

#mnt[x]>=0 where x is the usb port of the mount and mnt[x] is the line of the /dev/sdx1
global mnt
mnt=[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
d=["","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","",""]

global net_stat
net_stat = 1

global Brand

global connectbox_scroll

global max_partition
max_partiton = 0



def mountCheck():
    global mnt
    global loc
    global total
    global Brand
    global DEBUG

    # mnt is the matrix of /dev/sdx1 element
    # loc is the USBx element
    #total is the toal number of mounts currently
    #Brand is thee name of the host branding eg: ConnectBox
    # run the upgrade if it exsists
    a = Brand['usb0NoMount']
    if a == "1":
      logging.info("no mount set")
      print("no mount set")
      return
    total = 0
    j = 0                   #mount iterator looking for unmounted devices
    process = os.popen('lsblk')
    b = process.read()
    process.close()
    while (j < 11):
      if DEBUG > 2: print("loop 1, unmount",j)
      if (mnt[j] >= 0):
        if not ('sd'+chr(mnt[j])+'1' in b):
          c = '/dev/sd' + chr(mnt[j])+'1'
          print("unmount /dev/sd" + chr(mnt[j])+"1")
          c = 'umount '+c
          if DEBUG > 2: print("No longer present sd"+chr(mnt[j])+"1  so well "+c)
          if DEBUG > 2: print("the value of b is"+b)
          res = os.system(c)
          if DEBUG > 2: print("completed "+c)
          if res == 0:
            if loc[j] > ord('0'):
               process = os.popen('rmdir /media/usb'+chr(loc[j]))
               process.close()
               print("Deleted the directory /media/usb",chr(loc[j]))
            else:     #We just unmounted usb0 so we need to rerun the enhanced interfaceUSB loader
                      # Run these functions on mount -- added 20211111
              # Enhanced Content Load
              os.system("/usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py >/tmp/loadContent.log 2>&1 &")
            loc[j]=-1
            mnt[j] = -1
            j += 1
          else:
            if DEBUG > 2: print("Failed to " + c)
            mnt[j] = -1
            loc[j] = -1
            j += 1
        else:
        #Were here with the device still mounted
          print("device still mounted /dev/sd"+chr(mnt[j])+"1")
          j += 1
          total += 1
      else:
        #were here because there was no mount device detected
        if DEBUG > 2: print("device not mounted usb", j)
        j += 1
    i=0                       #line iterator
    j=0                       #used for finding sdx1's
    k=0                       #used for usb mount
    c = b.partition("\n")
# while we have lines to parse we check each line for an sdx1 device and mount it if not already
    while ((c[0] != "") and (i<35)):
      if DEBUG > 2: print("Loop 2, iterate:",i, c[0])
      d[i] = c[0]
      e=re.search('sd[a-z]1', d[i])
      if e:
        if not (('usb' in d[i]) or ('part /' in d[i])):     #True if were not mounted but should be
          a = ord('0')
          j = 9
          k = 0
          f=[-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
          while (k < 10):                                   #Find an empty spot to note a mount for usbX 
            if loc[k] == -1 and k < j:                      #find an empty location to do the mount recording
              j = k
            if loc[k] > 0:
              f[loc[k]-ord('0')]=loc[k]
            if DEBUG > 2: print("loop 3, iterate:",k)
            k += 1
          k=0;
          while (k <10) and (f[k] != -1):
            k += 1
          a = ord('0')+k
          if DEBUG > 2: print("end of loop were going to use location "+str(j)+" and ord "+chr(a))
          print("mount point is "+e.group())
# we have aproblem our mount point is to high.  we need to do a reboot.
#            os.system("/usr/sbin/reboot")
          time.sleep(20)    #This ends here.
# Now we know we need to do a mount and have found the lowest mount point to use in (a)
          if not (os.path.exists("/media/usb"+chr(a))):  #if the /mount/usbx isn't there create it
            res = os.system("mkdir /media/usb"+chr(a))
            if DEBUG > 2: print("created new direcotry %s","/media/usb"+chr(a))
          x = Popen(["uname", "-r"], stdout=PIPE)
          y = str(x.communicate()[0])
          x.stdout.close()
          if y>="5.15.0":
            b = "mount /dev/" + e.group() + " -t auto -o noatime,nodev,nosuid,sync,utf8" + " /media/usb" + chr(a)
          else:
            b = "mount /dev/" + e.group() + " -t auto -o noatime,nodev,nosuid,sync,iocharset=utf8" + " /media/usb" + chr(a)
          res = os.system(b)
          if DEBUG > 2: print("completed mount /dev/",e.group)
          mnt[j]=ord(e.group()[len(e.group())-2])
          loc[j]=a
          total += 1
          if a == ord('0'):
            # Run these functions on mount -- added 20211111
            # SSH Enabler
            os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")
            # upgrade enabler
            if (os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/upgrade/upgrade.py'")) == 0:
              print("starting the upgrade process\n")
              logging.info("starting the upgrade process")
              os.system("python3 /media/usb0/.connectbox/upgrade/upgrade.py")
            # Moodle Course Loader
#            os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/*.mbz && /usr/bin/php /var/www/moodle/admin/cli/restore_courses_directory.php /media/usb0/' >/tmp/restore_courses_directory.log 2>&1 &")
            # Enhanced Content Load
            if os.system("/usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py >/tmp/loadContent.log 2>&1 &")< 0:
                os.system("/usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py >/tmp/loadContent.log 2>&1 &")
        else:                                               #True if we are mounted, check for usb(?).
          if ('usb' in d[i]):                               #we need to register a mount or make sure it is
            a = d[i].partition('usb')
            if (a[2] != "") and (a[2].isalnum()):
              if len(a[2]) == 1:
                l = ord(a[2])
                k = 0
                j = 10
                while k<10:                                    #check through the current registered mounts
                  if loc[k] == -1 and k < j:
                    j = k
                  if loc[k] == l:
                    break
                  else:
                    k += 1
# We know know if we found usb? in the table if k < 10
                if k == 10 and j < 10:                          #mount was not in table to so add it
                  loc[j] = l                                  #set loc to usb(l) at j sice we didn't find it
                  mnt[j] = ord(e.group()[len(e.group())-2])   #set mnt to sd(?)1 finish the mount registration
                  if DEBUG > 2: print("/dev/"+e.group()+" is already mounted as usb"+chr(l)+"but we added it to the table")
                else:
                  if DEBUG > 2: print("/dev/"+e.group()+" was mounted and in the table at ",k)
              else:
                if DEBUG > 2: print("USB number >= 10 ", a[2], " We will unmount it")
                b = 'unmount /media/usb'+a[2]
                res = os.system(b)
            else:
              if DEBUG > 2: print("Error parsing usb# in line", i)
          else:
              if DEBUG > 2: print("/dev/sdx1 is already mounted but not as usb", d[i])
      c = c[2].partition("\n")
      i += 1
# now that we have looked at all lines in the current lsblk we need to count up the mounts
    j = -1
    i = 0
    while (i < 10):            # we will check a maximum of 10 mounts
      if DEBUG > 2: print("loop 4, iterate:",i)
      if (mnt[i] != -1):      # if mounted we move on
        if DEBUG > 2: print("Found a mount",i)
        i +=1
        j +=1
      else:                   # we have a hole or are done but need to validate
        k = i+1
        while (k < 11) and (mnt[i] == -1):  #checking next mount to see if it is valid
          if DEBUG > 2: print("loop 5, iterate:",k,i)
          if (mnt[k] != -1):
            mnt[i] = mnt[k]   # move the mount into this hole and clear the other point
            loc[i] = loc[k]   # move the location into this hole as well.
            mnt[k] = -1
            loc[k] = -1
            j += 1
            i += 1
            k += 1
            if DEBUG > 1: print("had to move mount to new location",k," from ",i)
          else:     # we have no mount here
            i += 1
            k += 1
    total = j+1
    if DEBUG > 1: print("total of devices mounted is", total)
    if DEBUG > 1: print("located sdX1 of", mnt)
    if DEBUG > 1: print("located ustX of", loc)
    return()



def do_resize2fs(rpi_platform, rp3_platform):

    global DEBUG
    global connectbox_scroll
    global max_partition

	# find the filesystem name ... like "/dev/mmcblk0p1"
#    out = pexpect.run('df -h')
#    p = re.compile('/dev/mmcblk[0-9]p[0-9]+')
#    out = out.decode('utf-8')
#    m = p.search(out)
#    FS = m.group()
#    if str(FS)[(len(str(FS))-1):]>str("0"):
#        if DEBUG: print("resize2fs complete...")
#        f = open(progress_file, "w")
#        f.write("resize2fs_done")
#        f.close()
#        os.sync()
#        return()
    if (rm3_platform == True):
      FS = "/dev/mmcblk1p"+str(max_partition)

    elif (rpi_platform == True):
      if connectbox_scroll == True: 
        FS = "/dev/mmcblk0p"+str(max_partition)
      else:
        FS = "/dev/mmcblk0p2"
    else:
        FS = "/dev/mmcblk0p1"
    cmd = 'resize2fs ' + FS
    out = pexpect.run(cmd, timeout=600)  # 10 minutes should be enough for the resize
    out = out.decode('utf-8')
    if "blocks long" in out:
        if DEBUG: print("resize2fs complete... now reboot")
        f = open(progress_file, "w")
        f.write("resize2fs_done")
        f.close()
        os.sync()
        logging.info("doing a reboot after the resize")
        os.system('shutdown -r now')


def do_fdisk(rpi_platform, rm3_platform):

    global DEBUG
    global connectbox_scroll
    global max_partition
    if not (rm3_platform):
      child = pexpect.spawn('fdisk /dev/mmcblk0', timeout = 10)
    else:
      child = pexpect.spawn('fdisk /dev/mmcblk1', timeout = 10)

    try:
      i = child.expect(['Command (m for help)*', 'No such file or directory']) # the match is looking for the LAST thing that came up so we need the *
    except:
      if DEBUG: print("Exception thrown during fdisk")
      if DEBUG: print("debug info:")
      if DEBUG: print(str(child))

  # the value of i is the reference to which of the [] arguments was found
    if i==1:
        if DEBUG: print("There is no /dev/mmcblk expected partition... ")
        child.kill(0)
        if not (rm3_platform):
          child = pexpect.spawn("fdisk /dev/mmcblk1", timeout = 10)
          try:
            i = child.expect(['Command(m for help)*', 'No such file or directory'])
          except:
            if DEBUG: print("Exception thrown during fdisk")
            if DEBUG: print("debug info:")
            if DEBUG: print(str(child))
          if i==1:
            if DEBUG: print("There is no /dev/mmcblk1 partiton.... kill child")
            child.kill(0)
    if i==0:
        if DEBUG: print("Found it!")
  # continuing

  # "p" get partition info and search out the starting sector of mmcblk0p1
    child.sendline('p')
    i = child.expect('Command (m for help)*')
  # the child.before contains all that came BEFORE we found the expected text
  #logging.info (child.before)
    response = child.before

  # change from binary to string
    respString = response.decode('utf-8')
    if respString.find("/dev/mmcblk0p5") >=0:
      connectbox_scroll = True
#      f = open(progress_file, "w")
#      f.write("fdisk_done")
#      f.close()
#      os.sync()
#      retun()
    else: connectbox_scroll = False
#   for CM4, we get one line beginning /dev/mmcblk0p1, 
#   and one line beginning /dev/mmcblk0p2 ... this is the line that we are looking for 

    if rm3_platform == True:
        x = 2
        while  respString.find("/dev/mmcblk1p"+str(x))>=0:
          x += 1
        x = x -1            # we will have found the last parttion then counted one more so decrement to get last partition
        max_partition = x
        p = re.compile('mmcblk[0-9]p'+str(x)+'\s*[0-9]+')        # create a regexp to get close to the sector info - CM4

#    if rpi_platform == True: 
    else:    # case for both RPi and NEO
        x = 2
        while  respString.find("/dev/mmcblk0p"+str(x))>=0:
          x += 1
        x = x -1						# we will have found the last parttion then counted one more so decrement to get last partition
        max_partition = x
        p = re.compile('mmcblk[0-9]p'+str(x)+'\s*[0-9]+')        # create a regexp to get close to the sector info - CM4


#    else:
#        p = re.compile('mmcblk[0-9]p[0-9]\s*[0-9]+')    # create a regexp to get close to the sector info - NEO

    m = p.search(respString)    # should find "mmcblk0p1   8192" or similar, saving as object m (NEO)
                                #  or "mmcblk0p2-9   532480" or similar for CM4
    match = m.group()           # get the text of the find
    p = re.compile('\s[0-9]+')  # a new regex to find just the number from the match above
    m = p.search(match)
    startSector = m.group()
    if DEBUG: print("starting sector = ", startSector )

  # "d" for delete the partition
    child.sendline('d')
    logging.info("delet partition")

    if rpi_platform or rm3_platform:    # CM4 & RM3 has 2 partitions... select partition 2
        i = child.expect('Partition number')
        child.sendline(str(x))
        logging.info("send partiton"+str(x))
    i = child.expect('Command (m for help)*')
    logging.info("found Command (m for help)*")
# print("after delete ",child.before)

  # "n" for new partition
    child.sendline('n')
    logging.info("Sent n for new partition")
    if rm3_platform:
      logging.info("looking for default 2 since were rm3_platform")
      i = child.expect('default 2')
      child.sendline(str(x))
      logging.info("sent partition number")
      i = child.expect('First sector')
      logging.info("Got First Sector question back")
    else:
      i = child.expect('(default p):*')
      logging.info("got back (default p):* question")
      # "p" for primary partition
      child.sendline('p')
      logging.info("Sent the p commannd")
      if rpi_platform:    # CM4 has 2 partitions... select partition 2
        logging.info("expecting 'default 2*' from RPI_Platform")
        i = child.expect('default 2*')
        logging.info("got the result and sending the stating sector")
        child.sendline(str(x))                 # "2" for partition number 2
        i = child.expect('default 2048*')
        logging.info("Ok expected default 2048* and got it")
# print("after new ",child.before)
      else:
          logging.info("not rpi_Platform so expecting default 1*")
          i = child.expect('default 1*')      # "1" for partition number 1
          logging.info("ok got it")
          child.sendline('1')
          logging.info("sent 1st partition")
          i = child.expect('default 2048*')
          logging.info("got default 2048* for starting sector")
# logging.info (child.before)

  # send the startSector number
    child.sendline(startSector)
    logging.info("sent starting sector")
    logging.info("after new starting sector came: ",child.before)
    logging.info("then :",child.after)
#    i = child.expect('Last*')
    logging.info("expected Last* and got it")
# print("At last sector... the after is: ", child.after)

  # take default for last sector
    child.sendline('\n')
    logging.info("sent balnk line to take default ending sector")
    i = child.expect('signature*')

  # "N" don't remove the signature
    child.sendline('N')
    i = child.expect('Command (m for help)*')

  # "w" for write and exit
    child.sendline('w')
    i = child.expect('Syncing disks*')

    logging.info("exiting the fdisk program... now reboot")
    f = open(progress_file, "w")
    f.write("fdisk_done   maxp="+str(max_partition))
    f.close()
    os.sync()
    # Disk is now the right size but the OS hasn't necessarily used it.
    logging.info( "PxUSBm is rebooting after fdisk changed")
    os.system('shutdown -r now')
    return()


# called by main()

def check_iwconfig(b):
# run iwconfig parameter and check for "Mode:Master"
# if found return 1 to indicate the wlan associated with the AP is up
#  else, return a 0

  wlanx = "wlan"+str(b)
# check to see if that did it...
  cmd = "iwconfig"
  rv = subprocess.check_output(cmd)
  rvs = rv.decode("utf-8").split(wlanx)

  if (len(rvs) >= 2):       # rvs is an array split on wlanx
    wlanx_flags = str(rvs[1]).find("Mode:Master")
    if (wlanx_flags) >= 1:
      # we are up
      return(1)
    else:
      return 0
  return(0)



def dbCheck():
       process = Popen(["/bin/systemctl","status","mysql"], shell = False, stdout=PIPE, stderr=PIPE)
       stdout, stderr = process.communicate()
       if stdout.find("active (running) since")>=0:
          return(0)
       else:
          process = Popen(["/bin/systemctl","restart","mysql"], shell = False, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          process = Popen(["/bin/systemctl","status","mysql"], shell = False, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          if stdout.find("active (running) since")>= 0:
              return(0)
       return(1)


def Revision():

  global DEBUG

  if DEBUG > 3: print("Started Revision test")
  revision = ""
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if 'Radxa CM3 IO' in line: revision = "RM3"
      elif "Revision" in line:
        logging.info("revision of hardware is: "+line)
        x = line.find(":")
        y = len(line)-1
        revision = line[(x+2):y]

    f.close()

    if len(revision) != 0:
      if str(revision)[0:0] == "0":
        revision = revision[0:3]
      if revision == '0003':  version="Pi B  256MB 1.0"
      elif revision== '0004':  version="PI B  256MB 2.0"
      elif revision== '0005':  version="Pi B  256MB 2.0"
      elif revision== '0006':  version="Pi B  256MB 2.0"
      elif revision== "0007":  version="PI A  256MB 2.0"
      elif revision== "0008":  version="PI A  256MB 2.0"
      elif revision== "0009":  version="PI A  256MB 2.0"
      elif revision== "000d":  version="PI B  512MB 2.0"
      elif revision== "000e":  version="PI B  512MB 2.0"
      elif revision== "000f":  version="PI B  512MB 2.0"
      elif revision== "0010":  version="PI B+ 512MB 1.0"
      elif revision== "0011":  version="CM1   512MB 1.0"
      elif revision== "0012":  version="PI A+ 256MB 1.1"
      elif revision== "0013":  version="PI B+ 512MB 1.2"
      elif revision== "0014":  version="CM1   512MB 1.0"
      elif revision== "0015":  version="PI A+ 512MB 1.1"
      elif revision== "a01040": version="PI 2B 1GB 1.0"
      elif revision== "a01041": version="PI 2B 1GB 1.1"
      elif revision== "a21041": version="PI 2B 1GB 1.1"
      elif revision== "a22042":  version="PI 2B 1GB 1.2"
      elif revision== "900021": version="PI A+ 512MB 1.1"
      elif revision== "900032": version='PI B+ 512MB 1.2'
      elif revision== "900092": version="PI Z  512MB 1.2"
      elif revision== "900093": version="PI Z  512MB 1.3"
      elif revision== "9000c1": version="PI ZW 512MB 1.1"
      elif revision== "a02082": version="PI 3B 1GB 1.2"
      elif revision== "a020a0": version="CM 3+ 1GB 1.0"
      elif revision== "a22082": version="PI 3B 1GB 1.2"
      elif revision== "a32082": version="PI 3B 1GB 1.2"
      elif revision== "a020d3": version="PI 3B+ 1GB 1.3"
      elif revision== "9020e0": version="PI 3A+ 512MB 1.0"
      elif revision== "a02100": version="CM3+ 1GB 1.0"
      elif revision== "a03111": version="PI 4B 1GB 1.1"
      elif revision== "b03111": version="PI 4B 2GB 1.1"
      elif revision== "b03112": version="PI 4B 2GB 1.2"
      elif revision== "b03114": version="PI 4B 2GB 1.4"
      elif revision== "c03111": version="PI 4B 4GB 1.1"
      elif revision== "c03112": version="PI 4B 4GB 1.2"
      elif revision== "c03114": version="PI 4B 4GB 1.4"
      elif revision== "d03114": version="PI 4B 8GB 1.4"
      elif revision== "902120": version="PI Z2W 512MB 1.0-"
      elif revision== "b03140": version="CM4 1GB 1.0"
      elif revision== "c03140": version="CM4 2GB 1.0"
      elif revision== "d03140": version="CM4 8GB 1.0"
      elif revision== "0000": version="NEO NANOPI"
      elif revision== "4" : version="OrangePi Zero 2"
      elif revision== "RM3" : version="Rock CM3"
      else:
        version="Unknown"
      return version
    else:
      # we have hit somthing we don't know
      try:
        process = os.popen("lshw -short")
        net_stats = process.read()
        process.close()
        version = "Unknown"
        x = net_stats.find("system")
        if x > 0:
          l = net_stats[x+6 :]
          y = l.find("\n") 
          l = l[0:y].rstrip().lstrip()
          logging.info("revision of hardware is : "+l)
          y = len(l)
          if y > 0:
            if ((l == "Orange Pi Zero2") or (l == "Orange Pi Zero 2") or (l == "OrangePi Zero2")):
              version = "OrangePiZero2"
            else:
              version = l
        return(version)
      except:
        return "Error"
  except:
    return "Error"

# setNetworkNames() is used to set names if they are not standard names for devices.

def setNetworkNames():
    # we look at the names and see if they match the standard style ethX, lo, wlanX format.  If not we create link files in
    # /etc/systemd/network/10-networkname.link
    # the contents of the link files will contain a short set of instructions:
    #
    # [Match]
    # MACAddress=xx:xx:xx:xx:xx
    # [Link]
    # Name=xxxxxx
    #
    # where in the above the mac address is the devices fixed address and the name is in the format of eth0, eth1.... or wlan0, wlan1, wlanX.....
    # if when we check the  names they are all in the standard format we exit.  Otherwise we check each one

    logging.info("got to set network names")
    print("Set network names")
    netwk = []
    ethntwk = []
    wlanntwk = []
    res = os.popen("lshw -c Network").read().split("*-network:")
    x = 0
    while ((len(res) > 0) and (x < (len(res)-1))):
        if len(res[x+1]) > 0:
            a = res[x+1]
            print("value x: "+str(x)+" value off line x+1: "+res[x+1])
            y = (a.find("logical name: "))
            if (y > 0):
                print("Found logical name:")
                y = y + 14
                b = a[y:].split("\n")
                ntwk = b[0]
                print("logical name: "+ntwk)
                logging.info("Found network name of device: "+ntwk)
                if len(ntwk) > 3:
                    if ((ntwk[-1].isnumeric()) and  (ntwk[0:-2] in "wlan eth")):
                        logging.info("Found port "+ntwk+" that is within our standard.")
                        print("Found port "+ntwk+" that is within our standard")
                        #Ok we have found a network name that is in the standard format.  We can move on.
                        if ((ntwk[0:-1]) == 'wlan'):
                            wlanntwk.append(ntwk[-1])
                            print("Wlan "+ntwk[-1])
                            x += 1
                        elif ((ntwk[0:-1]) == 'eth'):
                            ethntwk.append(ntwk[-1])
                            print("Eth "+ntwk[-1])
                            x += 1
                        else:
                            # we don't know what this is
                            x += 1					# ntwk holds the name of this odd port
                            print("Not sure what this port was "+ntwk)
                        continue
                    z = a.find("serial:")
                    print("serial z value is: "+str(z))
                    if z > 0:
                        b = a[(z+8):].split("\n")
                        idnt = b[0]
                        print("Serial number eg: mac is: "+idnt)
                        logging.info("Identifier for this network port is: "+idnt)
                        if ((len(idnt) > 0) and (len(idnt) < 18)):
                            #OK the name is not in the standard format and we will have to add a link file for this one.
                            #But we will first add it to the list that needs to be done.
                            netwk.append(tuple([ntwk,idnt]))
                            x += 1
                        else:
                            #didn't have a coorrectly formated identifier in the way of a mac address
                            logging.info("Couldn't get a mac address for port "+ntwk+" so having to skip it!")
                            x += 1
                    else:
                        #There was not a serial in the network list making it impossible to get the mac address
                        logging.info("Couldn't get a mac address for port "+ntwk+" so having to skip it!")
                        x += 1
                else:
                    x += 1							#Nothing to do since name was empty

            else:
                # We couldn't find any locial name: so no interfaces
                x += 1
        else:
            #The split is empty
            x +=1

# ok we have a list of network names in netwk.  If the length is > 0 we need to create the link files for the interfaces and then reboot.
# we also have wlanntwk list of wlanX devices where the list contains the X's
# we also have ethntwk list of ethX devicess where the list contains the X's

    print("length of wlanntwk is: "+str(len(wlanntwk))+" contents is: "+str(wlanntwk))
    print("length of ethntwk is: "+str(len(ethntwk))+" contents is: "+str(ethntwk))


    if (len(netwk) > 0):
        x = 0
        z = 0
        while (x < len(netwk)):
            if (netwk[x][0][0].lower() == 'e'):
                print("our list of ethernet ports is: "+str(ethntwk))
                #we found that we have an ethernet port that needs fixing
                y = 0
                while (str(y) in str(ethntwk)):
                    y += 1
                    while (os.path.isfile("/etc/systemd/network/"+str(y)+"0-e*.link")):
                        y += 1                #Now we know what ethX number to give this device.
                try:
                    path = "/etc/systemd/network/"+str(y)+"0-"+netwk[x][0]+".link"
                    if (not (os.path.isfile(path))):
                        f = open(path, "w")
                        print("writing ethernet file for "+path)
                        b = "[Match]\nMACAddress="+netwk[x][1]+"\n[Link]\nName=eth"+str(y)+"\n"
                        print("contents : "+b)
                        f.write(b)
                        ethntwk.append(y)
                        f.close()
                        os.sync()
                        z = 1			#Note we have written a definition file so a reboot will be required
                    else:
                        print("we already have our link file for this interface")
                except:
                    logging.info("Couldn't write the ethernet port link file for eth"+str(y))
                    print("couldnt write the etherent port file")
                    f.close()
            elif (netwk[x][0][0].lower() == 'w'):
                #We found that we have a Wifi port that needs fixing
                print("our list of wifi ports is: "+str(wlanntwk))
                y = 0
                while (str(y) in str(wlanntwk)):
                    y += 1
                    while (os.path.isfile("/etc/systemd/network/"+str(y)+"0-w*.link")):
                        y += 1
                #Now we know what wlanX number to give this device
                try:
                    path = "/etc/systemd/network/"+str(y)+"0-"+netwk[x][0]+".link"
                    if (not (os.path.isfile(path))):
                        f = open(path, "w")
                        print("writing wifi file for "+path)
                        b = "[Match]\nMACAddress="+netwk[x][1]+"\n[Link]\nName=wlan"+str(y)+"\n"
                        print("contents : "+b)
                        f.write(b)
                        wlanntwk.append(y)
                        f.close()
                        os.sync()
                        z = 1			#Note we have written a definition file so a reboot will be required
                    else:
                        print("we already have our link file for this interface")
                except:
                    logging.info("Couldn't write the wifi port link file for wlan"+str(y))
                    print("Couldn't write the wifi port file")
                    f.close()
                #this is an entry we don't recognize so we ignore it
                logging.info("Ignoring interface: "+netwk[x][0]+" with Mac address of : "+netwk[x][1])
                print("Ignorioing interface: "+netwk[x][0]+" with mac address of : "+netwk[x][1])

            x += 1				#Increment to the next entry if there is one


        if z != 0:				# Now that were done check to see if we need to call a reboot
            os.sync()
            print("We wrote new files so we reboot")
            os.system("sudo reboot")		#NOTE we will not return from here.   We will just restart.
    return




# getNetworkClass() ported from connectbox-hat-service / cli.py

def getNetworkClass(level):
    # this module is designed to get the available interfaces and define which interface is the client facing one and which is the
    # network facing interface.  The client interface is the AP interface and is based on either RTL8812AU or RTL8812BU or RTL88192U  The
    # network facing interface will use the on board BMC wifi module as long as an AP module is present.  If no AP module is present it will become
    # the AP although this is not optimal.  But this is useful for modules such as the RaspberryPi Zero W.

    # variable "level" defines the severity of the attempted fix to make all interfaces (eth0, wlan0, wlan1) functional.
    # A level = 1 is least severe.

#    global progress_file
    netwk=[]
    res = ""
    a = ""
    b = ""
#    logging.debug("starting the get network class tool of cli.py on the battery page")
    res = os.popen("lshw -c Network").read()
    i=3
    if "wlan" in res:
        r = res.split("wlan")
        while i > 1:
            if len(r) <= 1:
                a == ""
            else:
                a = r[1][0]
            if a != "":
                if r[1].find("driver="):
                    b = r[1].split("driver=")[1].split(" ")[0]             #Split out the driver from the configuration line
                    netwk.append([a,b])                                    #add the wlan# and driver to the list
                    logging.info("found wlan driver combo, wlan"+a+" driver: "+b)
                    a = ""
                    b = ""
                else:
                    b = "none"
            i = len(r)                                              #slice out the [0 and 1] sections of the split
            res = ""
            while i>1:
                r[len(r)-i] = r[len(r)-i+1]
                i -=1
            s = r.pop(len(r)-1)                                       #remove the last item in the list
            i = len(r)
    logging.info("We finished the wlan lookup and are now going to edit the files.")
    AP = ""                                                         #access point interface
    CI = ""                                                         #client interface
    if len(netwk) == 1:                                             #only one wlan interface AP only
        a = netwk[0][0]
        b = netwk[0][1]
        logging.info("single interface wlan"+a+" with driver "+b)
        # now we need to update the files for a single AP and no client
        AP = a;

    elif len(netwk) > 1:                                            #multiple wlan's so both AP and client interfaces
        logging.info("wlan"+netwk[0][0]+" with driver "+netwk[0][1])
        logging.info("wlan"+netwk[1][0]+" with driver "+netwk[1][1])
            # we have an rtl driver on this first wlan
        if "rtl88" in netwk[0][1]:                                  #if we have an rtl on the first wlan we will use it for AP
            AP = netwk[0][0]
            CI = netwk[1][0]
            #regardless of what we have there since its RTL-X we will use it for AP since we have no others
        elif "rtl88" in netwk[1][1]:                                  #if we have an rtl on the second wlan we will use it for AP
            AP = netwk[1][0]                                    #interface 2 has the rtl and will be AP
            CI = netwk[0][0]                                    #interface 1 is on board or other andd will be the client side for network
        elif "brcmfmac" in netwk[0][1]:
            AP = netwk[1][0]
            CI = netwk[0][0]
        else:
            AP = netwk[0][0]
            CI = netwk[1][0]



        logging.info("AP will be: wlan"+AP+" ethernet facing is: wlan"+CI)
        if len(netwk) >=3:
            logging.info("we have more interfaces so they must be manually managed") # if we have more than 2 interfaces then they must be manually managed. 
# --- no files changed (more than 2 interfaces... how to handle??) ---
            return(0)

    else:                                                           # we don't have even 1 interface
        logging.info("We have no wlan interfaces we can't function this way, rebooting to try to find the device")
# --- no files changed (no interfaces... maybe we missed one... how to handle??) ---
        return(0)

# with 1 or 2 interfaces we will always get to here with knowlege of AP and CI wlan's
# Now check to make sure our AP/CI pair agree with wificonfig.txt

    files_changed = fixfiles(AP,CI)     # Do any necessary fixing of the file entries - 
                                        #  return(1) indicates files changed and daemons restarted
    if files_changed == 1:
      level = 2                         # if files were changed, we need to do the full up/down package

    f = open(progress_file, "w")
    f.write("rewrite_netfiles_done")
    f.close()
    os.sync()

# here do: ifdown AP, ifup AP, ifconfig AP down, ifconfig AP up

# the following go pretty quick and may/should bring us up if the wlans didn't trade during boot
    if files_changed:
        os.system("ifdown wlan"+AP)
        os.system("ifup wlan"+AP)
        os.system("/bin/systemctl restart hostapd")
        os.system("/bin/systemctl restart dhcpcd")

        os.system("ifdown eth0")
        os.system("ifup eth0")

# Note: we do this AFTER the AP and eth0 down/ups to speed up AP startup as the CI startup
#        can happen while AP work is being done

    if ((check_CI()) or (check_wlan_CI(CI)) or (files_changed)):
      os.system("ifdown wlan"+CI)
      os.system("ifup wlan"+CI)


# --- signal from fixfiles() for a reboot (necessary ??)
    return(files_changed)


# fixFiles(a,c) was ported from connectbox-hat-service/cli.py

def fixfiles(a, c):
# This function is called to fix the files and restart the network daemons (if neeeded)
#    based on what we have loaded.
#  variable a: (AP) represents the Wlan that will serve as the Access point.
#  variable c: (CI) is the ethernet interface which may or may not be there.
#  (Note: the values of a and c are numbers only.)

# Entering here, we have a wificonfig.txt file which reflects status of previous power on...
#  and the status of all files to support that. If the lshw reveals the same situation,
#  we can safely just return without updating any files (return(0)). If, however, the lshw reveals something
#  different, we need to make appropriate changes to files and restart the services
#  (changed files indicated by return(1))

#  At the end of this function, wificonf.txt is written and reflects the settings in ALL required files
#   so if it is correct is wificonfig.txt, the supporting files are correct.

    global Brand

    logging.debug("Entering fix files")
    print("Entering fix files")

    at = ""
    ct = ["","",""]
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'r')
        at = f.read()
        ct = at.split("\n")
        f.close()
    except:
        pass
    logging.info("wificonf.txt holds "+ct[0]+" and "+ct[1]+" for detected paramaters (AP, Client) "+a+" and "+c)

    if ("AccessPointIF=wlan"+ a) == ct[0] and (("ClientIF=wlan"+ c == ct[1] and c!="") | (c == "" and ct[1] == "ClientIF=")):
        f = open("/etc/hostapd/hostapd.conf","r")
        g = f.read()
        f.close()
        if (Brand['Brand'] in g):
	        logging.info("Skipped file reconfiguration as the configuration is the same")
	        print("nothing to do")
#        os.system("ifup wlan"+a)   # restart wlan ... other restarts needed??n

# if wificonfig.txt agrees with info from lshw we can continue without changing anything
        	return(0)

# if NOT, we cook the files and will restart the services with
    res = os.system("/bin/systemctl stop networking.service")
    res = os.system("/bin/systemctl stop hostapd")
    res = os.system("/bin/systemctl stop dnsmasq")
    res = os.system("/bin/systemctl stop dhcpcd")

# we only come here if we need to adjust the network settings
# Lets start with the /etc/network/interface folder
    f = open('/etc/network/interfaces.j2','r', encoding='utf-8')
    g = open('/etc/network/interfaces.tmp','w', encoding='utf-8')
    x = 0
    skip_rest = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if skip_rest == 0:
            if '#CLIENTIF#' in l:       # #CLIENTIF# signals the end of AP and start of CI section
                x = 1                   #  signals we are in the ClientInterface section
            if 'wlan' in l:
                m = l.split('wlan')
                while (len(m)>1):

                    if x == 0:              # processing AP directives (this number is 0 until the CLIENTIF word is seen)
                         m[0] = m[0]+'wlan'+a                     #insert the AP wlan
#                    logging.debug("on interface line were setting $1: "+n)
                    else:                   # We are processing Client Interface directives
                        if c=="":
                            m[0] = '#'+m[0]+'wlan'+str(int(a)+1)
                        else:
                            if "#" == m[0][0]:
                                while m[0][1]=="#":             #take out any extra comment lines
# ?? colon in the next statement??
                                    m[0]=m[0][1:]
                                if len(m[0])<30:
# ?? colon in the next statement??
                                    m[0] = m[0][1:]             #if the line is not a real command line but a comment then take out the # in front ssince we have C
                        m[0] = m[0]+'wlan'+c

                    while m[1][0].isnumeric():
# ?? colon in next line??
                        m[1] = m[1][1:]                        #Remove numeric characters
                    z=1
                    m[0]=m[0]+m[1]
                    while z < (len(m)-1):
                        m[z]=m[z+1]
                        z += 1
                    m.pop()
                n = str(m[0])
            else:                           # all lines of the enumerate of interfaces.j2 which DON'T contain 'wlan'
                if x>0:                     # we are done with AccessPoint directives... on to Client Interface directives
                    if c == "":
                        skip_rest=1         #if we hit here and have no client ie: c="" then we skip the rest fo the file
                    if l != "\n" and c =="":
                        l = "#" + l            # if for some reason we don't have a #ClIENTIF# reverence theen we comment out all of the client if c=""   
                n = str(l)
            g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("we have finished the temp /etc/network/interfaces.tmp file")
# Now we are done with the /etc/netowrk/interface  file
# Lets work on the dnsmask.conf file

    f = open('/etc/dnsmasq.conf','r', encoding='utf-8')
    g = open('/etc/dnsmasq.tmp','w', encoding='utf-8')
    x = 0
    l = ""
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface=wlan'+a)
#             logging.debug("on dnsmasq were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             n = str(l)
        g.write(n)
    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/dnsmasq.tmp file")
# Now we are done with the /etc/dnsmasq.conf file
# lets move onto the hostapd.conf file

    f = open('/etc/hostapd/hostapd.conf','r', encoding='utf-8')
    g = open('/etc/hostapd/hostapd.tmp','w', encoding='utf-8')
    x = 0
    n = ""
    for y,l in enumerate(f):
        if 'interface=wlan' in l:
             m = l.split('interface=wlan')
             n = str(m[0]+'interface=wlan'+a)
#             logging.debug("on hostapd were setting $1: "+n)
             x += 1
             while m[1][0].isnumeric():
                   m[1] = m[1][1:]
             n = str(n + m[1])
        else:
             if 'ssid=' in l:
                 m = l.split("ssid=")
                 n = str(m[0]+ 'ssid=' + Brand['Brand'] + "\n")
             else:
                 n = str(l)
        g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/hostapd/hostapd.tmp file")

# Nowe we need to exclude the AP from Wpa_supplicant control

    f = open('/etc/dhcpcd.conf','r', encoding='utf-8')
    g = open('/etc/dhcpcd.tmp','w', encoding='utf-8')
    x = 0
    n = ""
    for y,l in enumerate(f):
        if 'wlan' in l:
            if 'denyinterfaces' in l:
                 m = l.split('denyinterfaces wlan')
                 if c=="":
                    n = str(m[0] + "\n")
                 else:
                    n = str(m[0]+"denyinterfaces wlan" + c + "\n")
#             logging.debug("on dhcpcd.conf were setting $1: "+n)
                 x += 1
            else:
                 m = l.split('interface wlan')
                 n = str(m[0]+'interface wlan' + a + "\n" )
                 x += 1
        else:
             n = str(l)
        g.write(n)

    g.flush()
    f.close()
    g.close()
    logging.debug("We have finished the temp /etc/dhcpcd.tmp file")

#  Now lets make sure we write out the configuration for future
#  (wificonf.txt reflects contents of all files which might need changes)
    try:
        f = open("/usr/local/connectbox/wificonf.txt", 'w')
        f.write("AccessPointIF=wlan"+ a +"\n")
        if c=="":
            f.write("ClientIF="+"\n")
        else:
            f.write("ClientIF=wlan"+ c +"\n")
        f.write("####END####\n")
        f.flush()
        f.close()
    except:
        pass

    os.system("sync")           #we will ensure we clear all files and pending write data

# Now we are done with the network/interface.tmp, dnsmasq.tmp and hostapd.tmp file creations time to put them into action.

    if a != "":
         logging.info("taking interface down wlan"+a)
         os.system("ifdown wlan"+a)

    if c != "":
         logging.info("taking interface down wlan"+c)
         os.system("ifdown wlan"+c)
    time.sleep(10)

#    logging.info("We have taken the interfaces down now")
    os.system("mv /etc/network/interfaces /etc/network/interfaces.bak")
    os.system("mv /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.bak")
    os.system("mv /etc/dnsmasq.conf /etc/dnsmasq.bak")
    os.system("mv /etc/dhcpcd.conf /etc/dhcpcd.bak")

    os.system("cp /etc/hostapd/hostapd.tmp /etc/hostapd/hostapd.conf")
    os.system("cp /etc/dnsmasq.tmp /etc/dnsmasq.conf")
    os.system("cp /etc/network/interfaces.tmp /etc/network/interfaces")
    os.system("cp /etc/dhcpcd.tmp /etc/dhcpcd.conf")

    os.system("/bin/systemctl daemon-reload")             #we reload all the daemons since we changed the config.
    time.sleep(5)
    print("finished fix files and exiting with a 1")
    logging.info("We have completed the file copies and daemon-reload")
#    logging.info("we will reboot to setup the new interfaces")

    return (1)      # indicates files were changed


def get_AP():
    f = open("/usr/local/connectbox/wificonf.txt", "r")
    wifi = f.read()
    f.close()
    apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
    AP = int(apwifi.split("wlan")[1])
    return(AP)

def get_CI():
    f = open("/usr/local/connectbox/wificonf.txt", "r")
    wifi = f.read()
    f.close()
    ciwifi = wifi.partition("ClientIF=")[2].split("\n")[0]
    try:
        CI = int(ciwifi.split("wlan")[1])
    except:
        CI = ""
    return(CI)

def check_CI():
  f = open("/etc/wpa_supplicant/wpa_supplicant.conf")
  connections = f.read()
  f.close()
  ci_active = connections.partition("ssid")
  x = ci_active[2].split("psk")
  if "Default1" in x[1]:
    return (0)        # we have no connection
  elif 'Default' in x[0]:
    return (0)		#We have no SSID
  else:
    return(1)



def check_eth0():
  process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
  stdout, stderr = process.communicate()
  net_stats = str(stdout).split("eth0")   # look for eth0 in ifconfig output
  if (len(net_stats) == 1):               # eth0 not found...  so we dont' have an issue
      return(0)
  x = net_stats[1].find("flags=")
  if (x>=0):
      y = net_stats[1].find("<")
      if (y > (x+6)):
          a = net_stats[1][(x+6):(y-1)]
          if a == '4099':
              return(0)				#were not connected so we just return ok
          elif a == '4163':
             if (net_stats[1].find("inet") <= 0):
                 try:
                     os.system("ifdown eth0")
                     os.system("ifup eth0")
                 except:
                     pass
                 process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
                 stdout, stderr = process.communicate()
                 net_stats = str(stdout).split("eth0")   # look for eth0 in ifconfig output
                 if (len(net_stats) != 1):     # eth0 not found... restart eth0
                     x = net_stats[1].find("flags=")
                     if (x>=0):
                         y = net_stats[1].find("<")
                         if (y > (x+6)):
                             a = net_stats[1][(x+6):(y-1)]
                             if a == '4099':
                                 return(0)				#were not connected so we just return ok
                             elif a == '4163':
                                 if (net_stats[1].find("inet") <= 0):
                                     return(1)
                                 else:
                                     return(0)
                 return(1)			#all other issues we error out.
             else:
                 return(0)                      #we have an ip so were good to go
          return(1)				#were in some wierd mode so we error
      return(1)					#we cant find the flags
  return(1)

def check_wlan_CI(CI):
  process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
  stdout, stderr = process.communicate()
  net_stats = str(stdout).split("wlan"+str(CI))   # look for wlan(CI) in ifconfig output
  if (len(net_stats)==1):     # wlan(CI) not found - return 1
    return(1)
  else:
    return(0)                 # wlan(CI) found... return 0


def check_stat_CI(CI):
    if (check_CI() == 0):
        return(0)	      #Were ok because we have not SSID set
    z = 0		      #If zero we  don't do anything
    process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    net_stats = str(stdout).split("wlan"+str(CI))
    if len(net_stats) > 1:
        x = net_stats[1].find("inet")
        y = net_stats[1].find("flags")
        if (x <= 0):  z = 1
        if (y >= 0):
             x = net_stats[1][(y+7):].find("<")
             if ((x >= 0) and (x > (y+7))):
                a = net_stats[1][(y+7):(x-1)]
                if a != '4163': z = 1
             else:
                 pass
        else:
            z = 0		#we don't have an interface for CI
    else:
        z = 1
    if (z != 0):
        try:
            os.system("ifdown  wlan"+str(CI))
        except:
            pass
        try:
            os.system("ifup wlan"+str(CI))
            return(0)
        except:
            return(1)
    return(0)			#Nothingg wrong we have a correct status.


def checkServices():		#check out the services that were supposed to start
    print("starting Check Services")
    logging.info("check services starting")
    process = Popen(["/bin/systemctl",'status','networking'], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    print("looking for networking.serice : "+str(x))
    if x < 0:
        print("Found networking not running")
        logging.info("Found networking not running")
        try:
            print("well have to retry the networking.service")
            logging.info("well we have to retry the networking.service")
            os.system("/bin/systemctl restart networking")			#Do the restart of networking
        except:
            #we failed to restart the networking service so don't know how to fix it since we have aleady reset the network files
            return(1)
        process = Popen(["/bin/systemctl","status","networking"], shell = False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        serva = str(stdout)
        x = serva.find("Active: active")
        print("line is: "+serva)
        print("looking for 'Active: active' have: "+str(x))
        if x > 0:
            print("OK we restarted networking.serices and were running")
            logging.info("OK we restarted the networking.service and were running")
            pass
        else:
            logging.info("OK we restarted the networking.service and were not running still")
            return(1)
        #we will continue aas we have a working networking service
        #We want to check the AP to make sure its up
    else:
        print("networking service running nicely")
        logging.info("Networking service was running nicely")

    logging.info("starting to test AP services")
    process = Popen(["/bin/systemctl","status", "hostapd"], shell=False, stdout=PIPE, stderr=PIPE) 
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    if x < 0:
      #We got here because the hostapd service is not running
      x = serva.find("Loaded: masked")
      if x >= 0:
        #Ok we have encountered hostapd masked for whatever reason
        logging.info("hostapd is masked and needs to be unmasked")
        process = Popen(['/bin/systemctl', 'unmask', 'hostapd'], shell =False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if stderr != "":
          logging.info("tried to unmask hostapd but got an error.  Don't know what to do now.")
      process = Popen(['/bin/systemctl', 'restart', 'hostapd'], shell=False, stdout=PIPE, stderr= PIPE)
      stdout, stderr = process.communicate()
      serva = str(stdout)
      if serva.find("Active: active") >= 0:
        logging.info("well the restart worked and is no longer masked")
        logging.info("hostapd may still have isseus but this is good")
      else:
        logging.info("tried to restart Hostapd but still didn't get an active service.  Don't know what to do now.")
    AP = "wlan"+str(get_AP())
    process = Popen(["/bin/systemctl",'status','ifup@'+AP], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    print("looking for ifup@AP.serice : "+AP+"and line is "+str(x))
    if x < 0:									#we found our AP ifup service not active
        print("Found the ifup@AP.service not running")
        logging.info("Found the ifup@AP.service not running")
        try:
            print("Going to have to try to restart the ifup@AP.service")
            logging.info("Going to have to try to restart the ifup@AP.service")
            os.system("/bin/systemctl restart ifup@"+AP)
            process = Popen(["/bin/systemctl","status","ifup@"+AP], shell=False, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            serva == str(stdout)
            x = serva.find("Active: active")
            if x > 0:
                try:
                    os.system("/bin/systemctl restart hostapd")
                    print("Ok we have succeeded in restarting ifup@AP.serice and have restarted hostapd as well")
                    logging.info("Ok we have succeded in restarting ifup@AP.service and have restarted hostapd as well")
                    pass
                except:
                    return(1) #We failed on the restart of hostapd after restarting wlanAP
                    logging.info("We failed on the restart of hostapd.service")
        except:
           logging.info("We failed on the restart of ifup@AP.service")
           return(1)								#We errored out on the retry of starting the ifup@AP service

       # If we are here then we have an ifup@AP that is loaded active and we fixed it.
    else:
        logging.info("We are loaded and active on ifup@AP.service")
        print("were loaded and running on the ifup@AP.service")


    # If we are here then we have an ifup@CI that is loaded active and we fixed it or CI is null so we skipped testing
    # now we need to test for our last item which is eth0

    logging.info("Strting the ifup@etho0.service test")
    process = Popen(["/bin/systemctl",'status','ifup@eth0'], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    if x < 0:									#we found our AP ifup service
        print("Ok we found the ifup@eth0.service not running")
        logging.info("Ok we found an ifup@eth0.service not running")
        try:
            print("Ok were going to try restarting the ifup@eth0.service")
            logging.info("OK we are going to try restarting the ifup@eth0.service")
            os.system("/bin/systemctl restart ifup@eath0")
            process = Popen(["/bin/systemctl","status","ifup@eath0"], shell=False, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            serva == str(stdout)
            x = serva.find("Active: active")
            if x > 0:
                print("Well we succeeded in restarting the ifup@eth0 service")
                logging.info("Well we succeded in restarting the ifup@eth0.service")
                pass								#Ok we succeeded in the restart were up and running.
            else:
                logging.info("We didn't succeed on the restart its still down")
                print("Well we didn't succeed on the restart of eth0 its still down")
                return(1)
        except:
           logging.info("We failed on the restart attempt of ifup@eth0.service")
           print("We failed on the restart attempt of ifupeth0.service")
           return(1)								#We errored out on the retry of starting the ifup@AP service

    else:
       print("ifup@eth0 service was running to begin with")
       logging.info("ifup@eth0 service was running to beging with")

    # If we are here then we have an ifup@eth0.service that is loaded active and/or we fixed it.

    logging.info("Starting CI services")
    # Now we need to check status of CI
    x = get_CI()
    y = check_CI()
    if  x != "" and y == 1:
        CI="wlan"+str(x)
        print("the total CI is now: "+CI)
        process = Popen(["/bin/systemctl",'status','ifup@'+CI], shell = False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        serva = str(stdout)
        x = serva.find("Active: active")
        print("looking for ifup@CI.serice : "+CI+"and line is "+str(x))
        if x < 0:									#we found our AP ifup service
            print("OK we dont have an ifup@CI.service")
            logging.info("OK we don't have an ifup@CI.service")
            try:
                print("Well were going to try restarting the ifup@CI.service")
                logging.info("Well were going to try restarting the ifup@CI.service")
                os.system("/bin/systemctl restart ifup@"+CI)
                process = Popen(["/bin/systemctl","status","ifup@"+CI], shell=False, stdout=PIPE, stderr=PIPE)
                stdout, stderr = process.communicate()
                serva == str(stdout)
                x = serva.find("Active: active")
                print("looking for active active have: "+str(x))
                if x > 0:
                    print("Ok we succeeded in the restarting of the ifup@CI.service")
                    logging.info("OK we succeded in the restarting of the ifup@CI.service")
            except:
                logging.info("We failed on the retry of the ifup@CI.service")
                print("We failed on the retry of the ifup@CI.service restart")
                return(1)							#We errored out on the retry of starting the ifup@CI service
        else:
            logging.info("The ifup@CI.service is running fine so nothing to do")
            print("The ifup@CI.service is running finel so nothiing to do")
    else:
        print("No CI on this device or Ci has no passwords and ssid so we skip")
        logging.info("No CI on this device ")

    print("OK were done with all our testing the services should be googd at this point")
    return(0)										#End of sequence testing were done all is well




if __name__ == "__main__":

# First handle the partition expansion
# Determine if we are on NEO or CM
    brand_file = '/usr/local/connectbox/brand.txt'
    rpi_platform = False
    global areadyconf
    global apwifi
    global clientwifi
    global PI_stat
    global stop_hostapd
    global ifupap
    global ifdownap
    global first_time
    global DEBUG
    global SSID
    global connectbox_scroll

    print(sys.argv[0])
    try:
        if sys.argv[1] != "":
            delay = int(sys.argv[1])
        else:
            delay = 30
    except:
        delay = 30

    DEBUG = 0
    SSID=""
    connectbox_scroll=False
    first_time=True
    stop_hostapd=False
    areadyconf= ""
    logging.info("Starting PxUSBm")
    version = Revision()                    # Get the version of hardware were running on
    if (version != "Unknown") and (version != "Error"):
      if version.find("OrangePiZero2")>=0: version  = "OZ2 "
      elif version.find("Orange") >=0: version = "OP? "
      elif version.find("Rock CM3") >=0: version = "RM3 "
    # see if we are NEO or CM
      x = version[3:].find(" ")
      if x >= 0:
          a = version[0:x+3].rstrip()
      else:
          a = version[0:4].rstrip()


    logging.info("PxUSBm Starting revision is "+version)
    try:
      f = open(brand_file, mode="r", encoding='utf-8')
      Brand = json.loads( f.read() )
      f.close
    except:
      f = open(brand_file, mode="w", encoding = 'utf-8')
      details  = {'Brand':"Connectbox", \
        'enhancedInterfaceLogo': "", \
        'Image':'connectbox_logo.png', \
        'Font': 27, \
        'pos_x': 6, \
        'pos_y': 0, \
        'Device_type': a, \
        "usb0NoMount": 0, \
        "lcd_pages_main": 1,\
        "lcd_pages_info": 1,\
        "lcd_pages_battery": 1,\
        "lcd_pages_multi_bat": 0,\
        "lcd_pages_stats_hour_one": 1,\
        "lcd_pages_stats_hour_two": 1,\
        "lcd_pages_stats_day_one": 1,\
        "lcd_pages_stats_day_two": 1,\
        "lcd_pages_stats_week_one": 1,\
        "lcd_pages_stats_week_two": 1,\
        "lcd_pages_stats_month_one": 1,\
        "lcd_pages_stats_month_two": 1,\
        "lcd_pages_admin": 0,\
        "Enable_MassStorage": "",\
        "g_device": "g_serial",\
        "otg": 0,\
        "server_url": "", \
        "server_authorization": "", \
        "server_sitename": "", \
        "server_siteadmin_name": "", \
        "server_siteadmin_email": "", \
        "server_siteadmin_phone": "", \
        "server_siteadmin_country": "" \
        }
      f.write(json.dumps(details))
      f.close
      f = open(brand_file, mode="r", encoding='utf8')
      Brand = json.loads(f.read())
    f.close

    NoMountUSB = Brand["usb0NoMount"] 			   # Note: brand is type dict, so no "find" method
    rpi_platform=False
    rm3_platform=False
    PI_stat = False
    OP_stat = False


# -- sort out the SSID

    if (version != "Unknown") and (version != "Error"):
      logging.info("Major type: "+a)
      if Brand["Device_type"].find(a)<=0:                    # Make sure the brand file is what we expect as were on this hardware.
        f = open(brand_file, mode="w", encoding = 'utf-8')
        Brand["Device_type"] = '"'+a+'"'
        Brand["lcd_pages_multi_bat"] = 0
        f.write(json.dumps(Brand))
        f.close()
        os.sync()
        SSID = Brand["Brand"]
    else:
        SSID = "ABC"
    x=SSID.find('"')                          #Remove all the quotation marks around the  SSID
    while ( x >= 0 and len(SSID)>0):
      SSID = SSID.replace('"','')
      x=SSID.find('"')

    logging.info("SSID from file is now: "+SSID)

    if 'CM' in Brand["Device_type"]:             #Now we determine what brand to work with
        rpi_platform=True
        PI_stat=True
        OP_stat=False

    if "PI" in Brand["Device_type"]:
        rpi_platform=True
        PI_stat=True
        OP_stat = False

    if "NEO" in Brand["Device_type"]:
        rpi_platform=False
        PI_stat=False
        OP_stat=False

    if "OZ2" in Brand["Device_type"]:
        rpi_platform = False
        PI_stat=False
        OP_stat =True

    if "RM3" in Brand["Device_type"]:
        rpi_platform = False
        rm3_platform=True
        PI_stat= False
        OP_stat=False
    if DEBUG > 3: print("Our device is type RPI platform:"+str(rpi_platform)+" and PI itself:"+str(PI_stat)+" and  Orange PI:"+str(OP_stat))
    net_stat = 1

    logging.info("device is RPI? "+str(rpi_platform)+" rm3_platform? "+str(rm3_platform)+" PI_stat? "+str(PI_stat)+" OP_stat? "+str(OP_stat))
    print("device is RPI? "+str(rpi_platform)+" rm3_platform? "+str(rm3_platform)+" PI_stat? "+str(PI_stat)+" OP_stat? "+str(OP_stat))

    # Sort out how far we are in the partition expansion process
    file_exists = os.path.exists(progress_file)
    if file_exists == False:
        logging.info("PxUSBm starting the fdisk operation for expansion")
        os.sync()
        do_fdisk(rpi_platform, rm3_platform)             # this ends in reboot() so won't return
    else:
        f = open(progress_file, "r")
        progress = f.read()
        f.close()
        if "fdisk_done" in progress:
            maxp = progress.split("maxp=")
            max_partition = maxp[1][0]
            logging.info("PxUSBm starting the resize2fs to format full disk")
            os.sync()
            do_resize2fs(rpi_platform, rm3_platform)     # this ends in reboot() so won't return

        else:
            logging.info("PxUSBm disk and format expansion already completed")
            print("PxUSBm disk and format expansion already completed")

# Once partition expansion is complete, handle the ongoing monitor of USB

# Major revision... remove the network testing from the module cli.py in connectbox-hat-service
#  and do a rewrite of those functions here.
#  Generally, the logic is:
#    - lshw -c network  // find which wlan is associated with mac 60:23:a4
#    - test lshw results against wificonf.txt
#      - if DIFFERENT, write the controlling files (/etc/network/interfaces, ++?) with the appropriate
#         wlan associations, ifdown/ifup/ifconfig down/ifconfig up for wlan0, wlan1, eth0
#      - if SAME, only do ifconfig down/ifconfig up for wlan0, wlan1, eth0 (faster)

# Call function to read lshw -c network and sort out whether we have correct association of
#  wlanx to the 8812au wifi module... check to see if the AP and CI agree with wificonfig.txt...
#  fix the required network file if needed... restart the wlan's

# Due to the new OS's not having fixed network names anymore.  We need to check the names and set them to expected types.
# This involves checking what the systems see's and has named them.  If necessary we create a link file to rename them and have to 
# reboot if necessary.

    logging.info("Getting Ready for Network Names and Network Class")
    print("Getting ready for network names and neewtwork class\n")

    setNetworkNames()
    print("finished setNetworkNames")

    getNetworkClass(1)  					# Note: calls fixfiles() if required... the (1) signals minimal ifconfig down/up
    print("Finished get network class")

    print("Checking on neo-battery-shutdown")
    x = -1
    while x < 0:
        process = Popen(["/bin/systemctl","status","neo-battery-shutdown"], shell=False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        x = str(stdout).find("Active: active (running)")
        if x < 0:
            logging.info("PxUSBm is restarting neo-battery-shutdown")
            print("PxUSBm is restarting neo-battery-shutdwon")
            process = os.popen("systemctl restart neo-battery-shutdown")
            process.close()
            time.sleep(5)
    print("neo-battery-shutdown is running")

    x = 95    # give time for network to come up before trying to fix it

    logging.info("PAUSING PXUSBM.PY FOR THE FOLLLOWING SECONDS "+str(delay))
    print("PUAUSING PXUSBM.PY FOR THE FOLLOWING SECONDS "+str(delay))
    time.sleep(delay)			#Sleep for 1 min to let the interfaces come up
    logging.info("DELAY COMPLETE STARTING CHECKING OF SERVICES!!")
    print("DELAY COMPLETE STARTING CHECKING OF SERVICES!!")

    if not (checkServices()): 			#This calls a check service routine that verifies that networking , ifup, ifdown came up and are running, otherwise
        time.sleep(5)				#it attemtps to fix them, but we only try twice then go on.
        checkServices()                         #we wait between attempts.

    logging.info("Getting ready to start Mount Checks")
    while (x == x):                         # main loop that we live in for life of running
          if (NoMountUSB <= 0):
             if DEBUG > 3: print("PxUSBm Going to start the mount Check")
             print("Getting ready for mount checks "+time.asctime())
             mountCheck()                   # Do a usb check to see if we have any inserted or removed.
             if connectbox_scroll: dbCheck()

          if ((x % 6)==0):
          # check to see if AP is still active
            AP = get_AP()
            AP_up = check_iwconfig(AP)  # returns 1 if up
            print("checking AP is up "+time.asctime())
            if (not AP_up):
              print("AP was not up and didn't  show correctly")
              try:
                  os.system("ifdown wlan"+str(AP))
              except:
                  pass
              try:
                  os.system("ifup wlan"+str(AP))
              except:
                  pass
              if not(check_iwconfig(AP)):
                  os.system("/bin/systemctl restart hostapd")
                  if not(check_iwconfig(AP)):
                     print("Still not up so having to resort to getNetworkClass")
                     getNetworkClass(1)       # try to fix the problem (shouldn't get here normally)

            check_eth0()      # make sure eth0 is up

            CI = get_CI()
            check_stat_CI(CI)

          if ((x % 10)==0):
            print("PxUSBm Going to do a Network check"+time.asctime())

# add check for /etc/wpa_supplicant/wpa_supplicant.conf for country=<blank>
            wpa_File = '/etc/wpa_supplicant/wpa_supplicant.conf'
            f = open(wpa_File, mode="r", encoding='utf-8')
            filedata=f.read()
            f.close()
            if 'country=\n' in filedata:
                filedata = filedata.replace('country=\n', 'country=US\n')
                with open(wpa_File, 'w') as f:
                  f.write(filedata)
                f.close() 

# check to see if brand.txt variable usb0NoMount has changed
            f = open("/usr/local/connectbox/brand.txt")
            Brand = json.loads( f.read() )
            f.close()
            NoMountUSB = Brand["usb0NoMount"] 			   # Note: brand is type dict, so no "find" method

# loop
          x += 1
          time.sleep(3)
# end of  while loop here

