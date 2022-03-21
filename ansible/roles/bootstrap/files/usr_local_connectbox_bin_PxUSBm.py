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
import logging
import re
import os
from subprocess import Popen, PIPE



# globals for Partion expansion
progress_file = '/usr/local/connectbox/expand_progress.txt'

# globals for USB monitoring
DEBUG = 0					#Debug 1 for netowrking, 2 for summary of mounts, 3 for detail of mounts
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
Brand = ""


def mountCheck():
    global mnt
    global loc
    global total
    global Brand

    # mnt is the matrix of /dev/sdx1 element
    # loc is the USBx element
    #total is the toal number of mounts currently
    #Brand is thee name of the host branding eg: ConnectBox

    try:
         f = open("/usr/local/connectbox/brand.txt", "r")
         a = f.read()
         f.close()
    except:
         a =  ""
    d = a.split('"')
    Brand = str(d[3])
    c = a.split('usb0NoMount":')
    a = str(c[1])
    if a[1] == "1":
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
          c = 'umount '+c
          if DEBUG > 2: print("No longer present sd"+chr(mnt[j])+"1  so well "+c)
          if DEBUG > 2: print("the value of b is"+b)
          res = os.system(c)
          if DEBUG > 2: print("completed "+c)
          if res == 0:
            if loc[j] > ord('0'):
               process = os.popen('rmdir /media/usb'+chr(loc[j]))
               process.close()
               if DEBUG > 2: print("Deleted the directory /media/usb",chr(loc[j]))
            else:     #We just unmounted usb0 so we need to rerun the enhanced interfaceUSB loader
                      # Run these functions on mount -- added 20211111
              # Enhanced Content Load
              os.system("/usr/bin/python /usr/local/connectbox/bin/enhancedInterfaceUSBLoader.py >/tmp/enhancedInterfaceUSBLoader.log 2>&1 &")
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
# Now e know we need to do a mount and have found the lowest mount point to use in (a)
          if not (os.path.exists("/media/usb"+chr(a))):  #if the /mount/usbx isn't there create it
            res = os.system("mkdir /media/usb"+chr(a))
            if DEBUG > 2: print("created new direcotry %s","/media/usb"+chr(a))
          b = "mount /dev/" + e.group() + " /media/usb" + chr(a)+ " -o noatime,nodev,nosuid,sync,iocharset=utf8"
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
            os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/upgrade/upgrade.py && (/bin/cp -r /media/usb0/.connectbox/upgrade/* /tmp) && /usr/bin/python3 /tmp/upgrade.py'")
            # Moodle Course Loader
            os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/*.mbz && /usr/bin/php /var/www/moodle/admin/cli/restore_courses_directory.php /media/usb0/' >/tmp/restore_courses_directory.log 2>&1 &")
            # Enhanced Content Load
            os.system("/usr/bin/python /usr/local/connectbox/bin/enhancedInterfaceUSBLoader.py >/tmp/enhancedInterfaceUSBLoader.log 2>&1 &")
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



def do_resize2fs(rpi_platform):
	# find the filesystem name ... like "/dev/mmcblk0p1"
    out = pexpect.run('df -h')
    p = re.compile('/dev/mmcblk[0-9]p[0-9]+')
    out = out.decode('utf-8') 
    m = p.search(out)
    FS = m.group()

    # we have the FS string, so build the command and run it
    if rpi_platform == True:
      FS = "/dev/mmcblk0p2"
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


def do_fdisk(rpi_platform):

    child = pexpect.spawn('fdisk /dev/mmcblk0', timeout = 10)
    try:
      i = child.expect(['Command (m for help)*', 'No such file or directory']) # the match is looking for the LAST thing that came up so we need the *
    except:
      if DEBUG: print("Exception thrown during fdisk")
      if DEBUG: print("debug info:")
      if DEBUG: print(str(child))

  # the value of i is the reference to which of the [] arguments was found
    if i==1:
        if DEBUG: print("There is no /dev/mmcblk0 partition... exiting")
        child.kill(0)
    if i==0:
        if DEBUG: print("Found it!")  
  # continuing

  # "p" get partition info and search out the starting sector of mmcblk0p1
    child.sendline('p')
    i = child.expect('Command (m for help)*')  
  # the child.before contains all that came BEFORE we found the expected text
  #print (child.before)  
    response = child.before

  # change from binary to string
    respString = response.decode('utf-8')

#   for CM4, we get one line beginning /dev/mmcblk0p1, 
#   and one line beginning /dev/mmcblk0p2 ... this is the line that we are looking for 
    if rpi_platform == True:
        p = re.compile('mmcblk[0-9]p2\s*[0-9]+')        # create a regexp to get close to the sector info - CM4
    else:
        p = re.compile('mmcblk[0-9]p[0-9]\s*[0-9]+')    # create a regexp to get close to the sector info - NEO

    m = p.search(respString)    # should find "mmcblk0p1   8192" or similar, saving as object m (NEO)
                                #  or "mmcblk0p2   532480" or similar for CM4
    match = m.group()           # get the text of the find
    p = re.compile('\s[0-9]+')  # a new regex to find just the number from the match above
    m = p.search(match)
    startSector = m.group()
    if DEBUG: print("starting sector = ", startSector )

  # "d" for delete the partition
    child.sendline('d')

    if rpi_platform == True:    # CM4 has 2 partitions... select partition 2
        i = child.expect('Partition number (1,2, default 2)*')
        child.sendline('2')

    i = child.expect('Command (m for help)*')
# print("after delete ",child.before)

  # "n" for new partition
    child.sendline('n')
    i = child.expect('(default p):*')
# print("after new ",child.before)

  # "p" for primary partition
    child.sendline('p')
    if rpi_platform == True:    # CM4 has 2 partitions... select partition 2
        i = child.expect('default 2*')
        child.sendline('2')                 # "2" for partition number 2         i = child.expect('default 2048*')
    else:
        i = child.expect('default 1*')      # "1" for partition number 1
        child.sendline('1')
        i = child.expect('default 2048*')
# print (child.before)

  # send the startSector number
    child.sendline(startSector)
    child.expect('Last sector*')
# print("At last sector... the after is: ", child.after)

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
    os.sync()
    logging.info( "PxUSBm is rebooting after fdisk changed")
    os.system('shutdown -r now')


def IP_Check(b, restart):
# IP_Check will check for an IP address on the AP and optionally try an ifdown/ifup if restart = True
# this routine returns 1 if the ip address is found.

     global ifupap
     global ifdownap

     process = Popen("ifconfig", shell = True, stdout=PIPE, stderr=PIPE)       #back to checking for an IP4 addresss
     stdout, stderr = process.communicate()
     net_stat = str(stdout).split("wlan")
     if len(net_stat)> (int(b)+1):
        if (len(net_stat)==1) or (not "inet" in net_stat[int(b)+1]):
            if restart:
               process = Popen(ifdownap, shell=True, stdout=PIPE, stderr=PIPE)
               stdout, stderr = process.communicate()
               time.sleep(5)
               process = Popen(ifupap, shell=True, stdout=PIPE, stderr=PIPE)
               stdout, stderr = process.communicate()
               time.sleep(20)
               process = Popen("ifconfig", shell = True, stdout=PIPE, stderr=PIPE)       #back to checking for an IP4 addresss
               stdout, stderr = process.communicate()
               net_stat = str(stdout).split("wlan")
               if len(net_stat)> (int(b)+1):
                 if (len(net_stat)==1) or (not "inet" in net_stat[int(b)+1]):
                   if DEBUG: print("did ifdown/ifup and still don't have an IP address "+net_stat[int(b)+1])
                   return(0)
                 else:
                   if len(net_stat) != 1:
                     return(1)
                   else: return(0)
               else: return(0)
            return(0)
        elif len(net_stat) != 1:
          return(1)
        else:
          return(0)
     else:
       return(0)



def ESSID_Check(b, restart):
# this routine ESSID_check will look to see if there is an ESSID assigned to the AP
# you pass this routine the wlan character and  if you want to attempt a restart of hostapd if no ESSID a restart value of True
# it will return a 1 if the ESSID is present and 0 otherwise

    process = Popen("iwconfig", shell=True, stdout=PIPE, stderr=PIPE)          # now well check for an ip address on the AP
    stdout, stderr = process.communicate()
    net_stat = str(stdout).split("wlan")                                       #split up iwconfig by wlan so the first wlan status is in net_stat[1]
    if ((len(net_stat) ==1) or (not "ESSID:" in net_stat[int(b)+1])):          #if we didn't find a " or no ESSID then we will try a down/up sequence for the wlan
      if DEBUG: print("did iwconfig but no ESSID present "+net_stat[int(b)+1])
      if restart:
          process = Popen("systemctl restart hostapd.service", shell=True, stdout=PIPE, stderr=PIPE) # lets restart hostapd and see if we can get our ESSID
          stdout, stderr = process.communicate()
          process = Popen("systemctl restart dnsmasq", shell=True, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          time.sleep(15)
          process = Popen("iwconfig", shell=True, stdout=PIPE, stderr=PIPE)	# we will check after the restart if we have an ESSID
          stdout, stderr = process.communicate()
          net_stat = str(stdout).split("wlan")
          if (len(net_stat) ==1 or (not "ESSID:" in net_stat[int(b)+1])):
            if DEBUG: print("Restarted hostapd and still didn't get the ESSID "+net_stat[int(b)+1])
            return(0)
          elif len(net_stat) != 1: return(1)
          else: return(0)
      else: return(0)
    elif(len(net_stat) != 1): return(1)
    else: return(0)


def NetworkCheck():

  # the ap is the access point wlan in the form of wlan0 or wlan1
  # the cl is the client access point wlan in the form of wlan0 or wlan1
  # the PI is ture if its a RPi (eg zero, 2, 3, 3a, 4) and false otherwise.

  global net_stat
  global areadyconf
  global Brand
  global apwifi
  global clientwifi
  global PI_stat
  global stop_hostapd
  global ifupap
  global ifdownap

  file_exists=True

  try:
    file_exists = os.path.exists("/var/run/network/*.pid")
  except:
    file_exists = False
  if file_exists == True:
    process = os.popen("ls /var/run/netowrk/*.pid")
    net_stats = process.read()
    process.close9()
    if ("ïfdown" in net_stats) or ("ifup" in net_stats):                  # if we are in the process of bring up or down wait.
      return;

  process = os.popen("systemctl status networking.service")            # we move on since hostapd should be running and if not theres nothging we can do.  So we check networking.services
  net_stats = process.read()
  process.close()
  if net_stats.find("Active: active") < 0:
    process = os.popen("systemctl start networking.service")           # networking services arn't running so lets restart them
    net_stats = process.read()
    process.close()
    time.sleep(5)
    if net_stats == "":
        process = os.popen("systemctl status networking.service")
        net_stats = process.read()
        process.close()
        if net_stats.find("Active: active") >= 0:
            logging.info("We were able to restart a stalled networking service")
            network_running=True
        else:
            logging.info("We were unable to start a stalled networking service")
            network_running=False
    else:
        logging.info("Attempt to restart networking.service failed with an error")
        network_running=False
  else:
    network_running=True
  process = os.popen("systemctl status dnsmasq")                       # moving on check dnsmasq
  net_stats = process.read()
  process.close()
  if net_stats.find("Active: active") < 0:
    process = os.popen("systemctl restart dnsmasq")                    # dnsmasq wasn't running so start it up
    net_stats = process.read()
    process.close()
    if net_stats.find("Active: active") >= 0:
        logging.info("we were able to start a stalled dnsmasq")
    else:
        logging.info("We were unable to start the dnsmasq service")

  process = os.popen("systemctl status hostapd.service")                  # we move on as were not in the process of bringing an interface up or down.
  net_stats = process.read()
  process.close()
  if net_stats.find("Loaded: masked")>= 0:                                # if for some reason hostapd is masked unmask it
    process = os.popen("systemctl unmask hostapd.service")
    net_stats = process.read()
    time.sleep(5)
    process.close()
    if net_stats.find("Removed")>=0:                                      # if for some reason hostapd is removed enable it
        process = os.popen("systemctl enable hostapd.service")
        net_stats = process.read()
        time.sleep(5)
        process.close()
        if net_stats.find("enabled hostapd")>=0:                          # if hostapd is enabled make sure it  is started
            process = os.popen("systemctl start hostapd.service")
            net_stats = process.read()
            process.close()
            time.sleep(5)
            if net_stats.find("failed")>=0:                               # if we failed to start hostapd not much we can do
                logging.info("failed to start hostapd error code is"+net_stats)
                hostapd_running=False
                if DEBUG: print("failed to start hostapd must be configuration error")
            else:
                logging.info("Succeeded in umasking, enabling and starting hostapd")
                hostapd_running=True
                if DEBUG: print ("succeeded in unmasking, enabling and starting hostapd")
        else:
              logging.info("Failed to enable hostapd after unmasking")
              hostapd_running=False
    else:
        logging.info("Failed to unmask hostapd")
        hostapd_running=False
  else:
    if net_stats.find("Loaded loaded") >= 0:                            #if hostapd is loaded: loaded it may not be running
      if net_stats.find("Active: active") <0:
        if net_stats.find("Failed to start") >0:                        # we found that hostapd is not running and failed to start.  likely due to a leftover run file on an improper shutdown
          # likely we can't start becasue of an old run file.
          process = os.popen("rm /var/run/hostapd/"+apwifi)
          res = process.read()
          process.close()
          if res.find("cannot remove") >0:
            logging.info("could not remove the run/hostapd/"+apwifi)
            hostapd_running=False
          else:
            res = os.popen("systemctl start hostapd.service")            # we found and removed an old run file on hostapd so lets restart it.
            net_stats = res.read()
            res.close()
            if net_stats.find("Active: active") >= 0:
              logging.info("Restarted hostapd and its running")
              hostapd_running=True
            else:
              logging.info("couldn't get hostapd running")
              hostapd_running=False
        else:
          logging.info("hostapd is not active but still failed to start???")
          hostapd_running=False
      else:
        hostapd_running=True                                           # hostapd was runnning find so lets move on
    else:
      if net_stats.find("Active: active") < 0:                         # hostapd was not loaded loaded so lets look and see if it is active active
        res = os.popen("systemctl start hostapd.service")              # hostapd wasn't active active so we start it up
        net_stats = res.read()
        res.close()
        if net_stats.find("Active: active") >= 0:
          logging.info("Restarted hostapd and its running")
          hostapd_running=True
        else:
          logging.info("couldn't get hostapd running")
          hostapd_running=False
      else:
        hostapd_running=True					       # were running and were fine



# We have finished the individual tests for networking.services, hostapd and dnsmasq and all are working to the best of our ability
# if we don't find the AP name in AP then lets try to restart the hostapd service

  b = apwifi[(len(apwifi)-1):]                                          # b contains the AP wifi character (0, 1, 2, .....)
  ifdownap = "ifdown "+apwifi
  ifupap = "ifup "+apwifi
  if clientwifi=="":
    c = chr(int(b)+1+ord("0"))
  else:
    c = clientwifi[(len(clientwifi)-1):]                                 # c contains the client wifi character (0, 1, 2, ...) if there was none then its one higher than AP

  #check the ESSID and if its not there try to restart the hostapd/dnsmasq
  if not hostapd_running:
    res = os.popen(ifdownap)
    res.close()
    if not(ESSID_Check(b, True)):
      logging.info("still couldn't get ESSID on retaRT OF Hostapd")
      if DEBUG: print("Couldn't get hostapd upd and running in startup and now even with ifdownap")
    res = os.popen("systemctl status hostapd")
    net_stats1 = res.read()
    res.close()
    if net_stats1.find("Active: active")>=0:
       hostapd_running=True
    else:
       hostapd_running=False  

  if not stop_hostapd:
    if (not ESSID_Check(b, True)): 					# if were not a RPi and ESSID missing or no AP
      valid_ESSID=False
      if (PI_stat and clientwifi==""):
         stop_hostapd=True
         if (not IP_Check(b,True)):
           valid_IP=False
           if DEBUG: print("have a PI version with no extra WIFI modules cant get IP address")
           logging.info("have PI version with no extra WIFI modules can't get an IP address for AP")
         else:
           valid_IP=True
           if (not ESSID_Check(b, True)):
             valid_ESSID=False
             if DEBUG: print("weve done our best to bring up the AP since this is a PI with no other WIFI modules")
             logging.info("weve done our best to bring up the AP since this is  a PI with no other WIFI modules")
           else:
             valid_ESSID=True
      else:
        if (not IP_Check(b, True)):					# now well check for an ip address on the AP
          valid_IP=False
          if (not ESSID_Check(b, True)):				# Ok so we couldn't get the interface up but now we reset hostapd so lets try an up/downn again
            valid_ESSID=False 
            if DEBUG: print("We cant get an ESSID and we didn't get an IP.... what to do?")
            logging.info("We can't get an ESSID and we didn't get and IP..... what to do?")
          else:								#this time we got an IP but still don't have an ESSID so try an up/down again
            valid_ESSID=True
            if (not IP_Check(b, True)):					#We check for an IP address now that we have an  ESSID
              valid_IP=False
              if DEBUG: print("Well we got an ESSID but failed at getting the IP... what to do?")
              logging.info("We got the ESSID on the second ifdown/ifup but still couldn't get an IP")
            else:
              valid_IP=True
        else:
          valid_IP=True
          if valid_ESSID==False:
            if (not ESSID_Check(b, True)):
              valid_ESSID=False
              stop_hostapd=True						#we have tried three times so were going to  hope were up.
            else: valid_ESSID=True
    else:
      valid_ESSID=True 
      if (not IP_Check(b, True)):					#Check to make sure we have an ip now that we have an ESSID
         valid_IP=False
         if DEBUG: print("We have an essid but can't get an IP....")
         logging.info("We have an ESSID but we couldn't get an IP address... what to do?")
      else: valid_IP=True						#We got a valid ESSID the first time and got a valid IP
  else:
    if (not ESSID_Check(b,False)):
      valid_ESSID=False
    else:
      valid_ESSID=True									#were here because were a PI and have not other WIFI's so just check the IP address
    if (not IP_Check(b,True)):
      valid_IP=False
    else:
      valid_IP=True

  if valid_IP and valid_ESSID and hostapd_running and network_running: print("AP up and running ok")
  else: print("Not everything is clean: IP, ESSID, hostapd, network, stop_hostapd ",valid_IP, valid_ESSID, hostapd_running, network_running, stop_hostapd)
  res = os.popen("ls /sys/class/net")
  SysNetworks = res.read().split()
  res.close()
  for netx in SysNetworks:                                                # Look at each interface
    if netx != "":
      try:
          process = os.popen("cat /sys/class/net/"+netx+"/operstate")     #check the operational state of all interfaces
          net_stats = process.read()
          process.close()
          if net_stats.find("down") >= 0 :                                # if its down lets try to raise it
            if areadyconf.find(netx) < 0 :                                # Were checking to see if we should leave this network alone
                cmd = "ifup "+netx
                process = Popen([cmd],shell=True, stdout=PIPE, stderr=PIPE)
                (output, error) = process.communicate()
                process.terminate()
                if str(error).find("already configured")>=0:
                  areadyconf =  netx + "," + areadyconf
                  logging.info("Interface "+netx+" is already configured")
                else:
                  process = os.popen("cat /sys/class/net/"+netx+"/operstate")
                  net_stats = process.read()
                  process.close()
                  if net_stats.find("up") >= 0:
                      logging.info("raised interface "+netx)              #We were successful at rasing the interface
                  else:
                    if netx != clientwifi:  #eg: its not client so it mus be AP
                        net_stat += 1
      except:
          logging.info("Interface "+netx+"is not yet configured for up/down")
  if (net_stat >= 10) and (not stop_hostapd):
    logging.info("Network startup issues.  Will try to restart services")
    for netx in SysNetworks:
        if netx != "":
            try:
                process = os.popen("cat /sys/class/net/"+next+"/operstate")
                net_stats = process.read()
                process.close()
                if net_stats == "up":
                    process = os.popen("ifdown "+netx)
                    time.sleep(5)
                    ex_stat = process.read()
                    process.close()
                    process = os.popen("cat /sys/class/net/"+next+"/operstate")
                    net_stats = process.read()
                    process.close()
                    ex_stat == net_stats
                    if ex_state == 'up':
                      logging.info("couldn't take down "+netx)
            except:
                  logging.info("Interface "+netx+" needs to be configured")
    logging.info("stopped all interfaces as much as possible")   
#restart networking
    try:
        res = os.popen("systemctl resart networking.service")
        res.close()
    except:
        logging.info("networking.service has configuration issues")
    proess = os.popen("systemctl status networking.service")
    res = process.read()
    process.close()
    if res.find("active (exited)") <= 0:
      logging.info("networking.service failed to start")
# restart dnsmasq
    try:
        process = os.popen("systemctl restart dnsmasq")
        process.close()
        time.sleep(5)
    except:
        logging.info("dnsmasq has configuration issues")
# restart dnsmasq
    try:
        process = os.popen("systemctl status dnsmasq")
        process.close()
    except:
        logging.info("dnsmasq service failed to start")
# restart hostapd
    if not stop_hostapd:
      try:
        process = os.popen("systemctl restart hostapd")
        process.close()
        process = os.popen("systemctl restart dnsmasq")
        process.close()
        time.sleep(5)
      except:
        logging.info("hostapd service has configuration issues")
    process = os.popen("systemctl status hostapd")
    res = process.read()
    process.close()
    if res.find("active (exited)") <0:
      logging.info("hostapd service failed to start")
    net_stat = 0
    areadyconf = ""



def Revision():
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if "Revision" in line:
        print(line)
        x = line.find(":")
        y = len(line)-1
        revision = line[(x+2):y]
    f.close()
  
    if str(revision)[0:0] == "0":
      revision = revision[0:3]
    elif revision == '0003':  version="Pi B  256MB 1.0"
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
    elif revision== "a02100": version="CM 3+ 1GB 1.0"
    elif revision== "a03111": version="PI 4B 1GB 1.1"
    elif revision== "b03111": version="PI 4B 2GB 1.1"
    elif revision== "b03112": version="PI 4B 2GB 1.2"
    elif revision== "b03114": version="PI 4B 2GB 1.4"
    elif revision== "c03111": version="PI 4B 4GB 1.1"
    elif revision== "c03112": version="PI 4B 4GB 1.2"
    elif revision== "c03114": version="PI 4B 4GB 1.4"
    elif revision== "d03114": version="PI 4B 8GB 1.4"
    elif revision== "902120": version="PI Z2W 512MB 1.0-"
    elif revision== "b03140": version="CM 4 2GB 1.0"
    elif revision== "d03140": version="CM 4 8GB 1.0"
    elif revision== "0000": version="NEO NANOPI 1GB 1.1"
    else:
      version="Unknown" 
    return version
  except:
    return "Error"



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

    stop_hostapd=False
    areadyconf= ""

    version = Revision()                    # Get the version of hardware were running on
    print("revision is "+version)
    if (version != "Unknown") and (version != "Error"):
    # see if we are NEO or CM
      f = open(brand_file,"r")
      brand = f.read()
      f.close()
      a = version[0:2].rstrip()
      print("Major type: "+a)
      if brand.find(a)<=0:                    # Make sure the brand file is what we expect as were on this hardware.
        f = open(brand_file, "w")
        x = brand.find('"Device_type":')
        y = brand[(x+14):].find(',')
        print("Writing new brand file entry at:",x,y)
        a = brand[0:(x+14)]+' "'+a+'"'+brand[(x+14+y):]
        if a.find("CM")>0 :
          x = a.find('"lcd_pages_multi_bat": ')
          if x>0: a=a[0:(x+22)] + '1' + a[(x+24):]
        else:
          x = a.find('"lcd_pages_multi_bat": ')
          if x>0: a=a[0:(x+22)] + '0' + a[x(+24):]
        print("final text is: "+a)
        f.write(a)
        f.close()
        os.sync()

    if 'CM' in brand:                       #Now we determine what brand to work with
        rpi_platform=True
        PI_stat=True

    if "PI" in brand:
        rpi_platform=True
        PI_stat=True

    if "NEO" in brand:
        rpi_platform=False
        PI_stat=False


    net_stat = 1
    x = 98
    # Sort out how far we are in the partition expansion process
    file_exists = os.path.exists(progress_file)
    if file_exists == False:
        do_fdisk(rpi_platform)             # this ends in reboot() so won't return
    else: 
        f = open(progress_file, "r")
        progress = f.read()
        f.close()
        if "fdisk_done" in progress:
            do_resize2fs(rpi_platform)     # this ends in reboot() so won't return

# Once partition expansion is complete, handle the ongoing monitor of USB

        # we get through when neo-battery-shutdown is runningps
        logging.info("got through the neo-battery-shutdown running test")
        if ("rewrite_netfiles_done" in progress or "running" in progress):
            f = open("/usr/local/connectbox/wificonf.txt", "r")
            wifi = f.read()
            f.close()
            clientwifi =  wifi.partition("ClientIF=")[2].split("\n")[0]
            apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
            print("Client interface is ", clientwifi)
            print("AP interface is ", apwifi)

        if PI_stat:
          process = Popen("lshw -C Network", shell=True, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          b =apwifi[(len(apwifi)-1):]
          wifi = str(stdout).split("wlan")
          wifid= str(wifi[int(b)+1]).split("driver=")
          if DEBUG: print(wifid[1])
          if "brcfmac" in wifid[1]:
            PI_stat = False
            print("cancled the PI_status")


        while True:
          if not os.path.exists("/usr/local/connectbox/PauseMount"):
             mountCheck()
          if (x % 100) == 0:
             NetworkCheck()
          time.sleep(3)
          y = 0
          x += 1 
          if x > 2500:
             x = 0
             net_stat +=1
             proc = os.popen("systemctl status neo-battery-shutdown").read()
             while (proc.find("Active: inactive") or proc.find("Active: failed")) and y<5:
             # we found the neo-battery-shutdown not running lets try to restarat
                proc = os.popen("systemctl restart neo-battery-shutdown").read()
                time.sleep(10)
                proc = os.popen("systemctl status neo-battery-shutdown").read()
                y += 1

