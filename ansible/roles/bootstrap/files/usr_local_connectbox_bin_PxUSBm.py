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
progress_file = '/usr/local/connectbox/bin/expand_progress.txt'

# globals for USB monitoring
DEBUG = 0
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


def mountCheck():
    global mnt
    global loc
    global total
    try:
         f = open("/usr/local/connectbox/brand.txt", "r")
         a = f.read()
         f.close()
    except:
         a =  ""
    c = a.split('usb0NoMount": ')
    a = str(c[1])
    if a[1] == "1":
      return
    total = 0
    j = 0                   #mount iterator looking for unmounted devices
    process = os.popen('lsblk')
    b = process.read()
    process.close()
    while (j < 11):
      if DEBUG: print("loop 1, unmount",j)
      if (mnt[j] >= 0):
        if not ('sd'+chr(mnt[j])+'1' in b):
          c = '/dev/sd' + chr(mnt[j])+'1'
          c = 'umount '+c
          if DEBUG: print("No longer present sd"+chr(mnt[j])+"1  so well "+c)
          if DEBUG: print("the value of b is"+b)
          res = os.system(c)
          if DEBUG: print("completed "+c)
          if res == 0:
            if loc[j] > ord('0'):
               process = os.popen('rmdir /media/usb'+chr(loc[j]))
               process.close()
               if DEBUG: print("Deleted the directory /media/usb",chr(loc[j]))
            else:     #We just unmounted usb0 so we need to rerun the enhanced interfaceUSB loader
                      # Run these functions on mount -- added 20211111
              # Enhanced Content Load
              os.system("/usr/bin/python /usr/local/connectbox/bin/enhancedInterfaceUSBLoader.py >/tmp/enhancedInterfaceUSBLoader.log 2>&1 &")
            loc[j]=-1
            mnt[j] = -1
            j += 1
          else:
            if DEBUG: print("Failed to " + c)
            mnt[j] = -1
            loc[j] = -1
            j += 1
        else:
        #Were here with the device still mounted
          j += 1
          total += 1
      else:
        #were here because there was no mount device detected
        if DEBUG: print("device not mounted usb", j)
        j += 1
    i=0                       #line iterator
    j=0                       #used for finding sdx1's
    k=0                       #used for usb mount
    c = b.partition("\n")
# while we have lines to parse we check each line for an sdx1 device and mount it if not already
    while ((c[0] != "") and (i<35)):
      if DEBUG: print("Loop 2, iterate:",i, c[0])
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
            if DEBUG: print("loop 3, iterate:",k)
            k += 1
          k=0;
          while (k <10) and (f[k] != -1):
            k += 1
          a = ord('0')+k
          if DEBUG: print("end of loop were going to use location "+str(j)+" and ord "+chr(a))
# Now e know we need to do a mount and have found the lowest mount point to use in (a)
          if not (os.path.exists("/media/usb"+chr(a))):  #if the /mount/usbx isn't there create it
            res = os.system("mkdir /media/usb"+chr(a))
            if DEBUG: print("created new direcotry %s","/media/usb"+chr(a))
          b = "mount /dev/" + e.group() + " /media/usb" + chr(a)+ " -o noatime,nodev,nosuid,sync,iocharset=utf8"
          res = os.system(b)
          if DEBUG: print("completed mount /dev/",e.group)
          mnt[j]=ord(e.group()[len(e.group())-2])
          loc[j]=a
          total += 1
          if a == ord('0'):
            # Run these functions on mount -- added 20211111
            # SSH Enabler
            os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")
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
                  if DEBUG: print("/dev/"+e.group()+" is already mounted as usb"+chr(l)+"but we added it to the table")
                else:
                  if DEBUG: print("/dev/"+e.group()+" was mounted and in the table at ",k)
              else:
                if DEBUG: print("USB number >= 10 ", a[2], " We will unmount it")
                b = 'unmount /media/usb'+a[2]
                res = os.system(b)
            else:
              if DEBUG: print("Error parsing usb# in line", i)
          else:
              if DEBUG: print("/dev/sdx1 is already mounted but not as usb", d[i])
      c = c[2].partition("\n")
      i += 1
# now that we have looked at all lines in the current lsblk we need to count up the mounts
    j = -1
    i = 0
    while (i < 10):            # we will check a maximum of 10 mounts
      if DEBUG: print("loop 4, iterate:",i)
      if (mnt[i] != -1):      # if mounted we move on
        if DEBUG: print("Found a mount",i)
        i +=1
        j +=1
      else:                   # we have a hole or are done but need to validate
        k = i+1
        while (k < 11) and (mnt[i] == -1):  #checking next mount to see if it is valid
          if DEBUG: print("loop 5, iterate:",k,i)
          if (mnt[k] != -1):
            mnt[i] = mnt[k]   # move the mount into this hole and clear the other point
            loc[i] = loc[k]   # move the location into this hole as well.
            mnt[k] = -1
            loc[k] = -1
            j += 1
            i += 1
            k += 1
            if DEBUG: print("had to move mount to new location",k," from ",i)
          else:     # we have no mount here
            i += 1
            k += 1
    total = j+1
    if DEBUG: print("total of devices mounted is", total)
    if DEBUG: print("located sdX1 of", mnt)
    if DEBUG: print("located ustX of", loc)
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
      if DEBUG: print("Exception thrown")
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


def NetworkCheck():

  global net_stat
  global areadyconf

  process = os.popen("systemctl status hostapd")
  net_stats = process.read()
  process.close()
  if net_stats.find("Loaded: masked")>= 0:
    process = os.popen("systemctl unmask hostapd.service")
    net_stats = process.read()
    process.close()
    if net_stats.find("Removed")>=0:
        process = os.popen("systemctl enable hostapd.service")
        net_stats = process.read()
        process.close()
        if net_stats.find("enabled hostapd")>=0:
            process = os.popen("systemctl start hostapd.service")
            net_stats = process.read()
            process.close()
            if net_stats.find("failed")>=0:
                logging.info("failed to start hostapd error code is"+net_stats)
                if DEBUG: print("failed to start hostapd must be configuration error")
            else:
                logging.info("Succeeded in umasking, enabling and starting hostapd")
                if DEBUG: print ("succeeded in unmasking, enabling and starting hostapd")
        else:
              logging.info("Failed to enable hostapd after unmasking")
    else:
        logging.info("Failed to unmask hostapd")
  else:
    if net_stats.find("Loaded loaded") >= 0:
      if net_stats.find("Active: active") <0:
        if net_stats.find("Failed to start") >0:
          # likely we can't start becasue of an old run file.
          process = os.popen("rm /var/run/hostapd/"+apwifi)
          res = process.read()
          process.close()
          if res.find("cannot remove") >0:
            logging.info("could not remove the run/hostapd/"+apwifi)
          else:
            res = os.popen("systemctl start hostapd")
            net_stats = res.read()
            res.close()
            if net_stats.find("Active: active") >= 0:
              logging.info("Restarted hostapd and its running")
            else:
              logging.info("couldn't get hostapd running")
        else:
          logging.info("hostapd is not active but still failed to start???")
      else:
        pass    #were running and were fine
    else:
      if net_stats.find("Active: active") < 0:
        res = os.popen("systemctl start hostapd")
        net_stats = res.read()
        res.close()
        if net_stats.find("Active: active") >= 0:
          logging.info("Restarted hostapd and its running")
        else:
          logging.info("couldn't get hostapd running")
      else:
        pass    # were running and were fine

  process = os.popen("systemctl status networking.service")
  net_stats = process.read()
  process.close()
  if net_stats.find("Active: active") < 0:
    process = os.popen("systemctl start networking.service")
    net_stats = process.read()
    process.close()
    if net_stats == "":
        process = os.popen("systemctl status networking.service")
        net_stats = process.read()
        process.close()
        if net_stats.find("Active: active") >= 0:
            logging.info("We were able to restart a stalled networking service")
        else:
            logging.info("We were unable to start a stalled networking service")
    else:
        logging.info("Attempt to restart networking.service failed with an error")

  process = os.popen("systemctl status dnsmasq")
  net_stats = process.read()
  process.close()
  if net_stats.find("Active: active") < 0:
    process = os.popen("systemctl restart dnsmasq")
    net_stats = process.read()
    process.close()
    if net_stats.find("Active: active") >= 0:
        logging.info("we were able to start a stalled dnsmasq")
    else:
        logging.info("We were unable to start the dnsmasq service")


  res = os.popen("ls /sys/class/net")
  SysNetworks = res.read().split()
  res.close()
  for netx in SysNetworks:
    if netx != "":
      try:
          process = os.popen("cat /sys/class/net/"+netx+"/operstate")          
          net_stats = process.read()
          process.close()
          if net_stats.find("down") >= 0 :
            if areadyconf.find(netx) < 0 :        # Were checking to see if we should leave this network alone
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
                      logging.info("raised interface "+netx)
                  else:
                    if netx != clientwifi:  #eg: its not client so it mus be AP
                        net_stat += 1
      except:
          logging.info("Interface "+netx+"is not yet configured for up/down")
  if net_stat >= 10:
    logging.info("Network startup issues.  Will try to restart services")
    for netx in SysNetworks:
        if netx != "":
            try:
                process = os.popen("cat /sys/class/net/"+next+"/operstate")
                net_stats = process.read()
                process.close()
                if net_stats == "up":
                    process = os.popen("ifdown "+netx)
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
        res = process.read()
        process.close()
    except:
        logging.info("dnsmasq has configuration issues")
# restart dnsmasq
    try:
        process = os.popen("systemctl status dnsmasq")
        res = process.read()
        process.close()
    except:
        logging.info("dnsmasq service failed to start")
# restart hostapd
    try:
        process = os.popen("systemctl restart hostapd")
        res = process.read()
        process.close()
    except:
        logging.info("hostapd service has configuration issues")
    process = os.popen("systemctl status hostapd")
    res = process.read()
    process.close()
    if res.find("active (exited)") <0:
      logging.info("hostapd service failed to start")
    net_stat = 0
    areadyconf = ""




if __name__ == "__main__":

# First handle the partition expansion
# Determine if we are on NEO or CM
    brand_file = '/usr/local/connectbox/brand.txt'
    rpi_platform = False
    global areadyconf
    areadyconf= ""

    # see if we are NEO or CM
    f = open(brand_file,"r")
    brand = f.read()
    f.close()
    if 'CM' in brand:
        rpi_platform = True
    if "PI" in brand:
        rpi_platform = True
    net_stat = 1
    x = 0
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

# Once partition expansion is complete, handle the ongoing monitor of USBs

        proc = os.popen("systemctl status neo-battery-shutdown").read()
        while (proc.find("Active: inactive") or proc.find("Active: failed"):
            # we found the neo-battery-shutdown not running lets try to restarat
            proc = os.popen("systemctl restart neo-battery-shutdown").read()
            proc = os.popen("systemctl status neo-battery-shutdown").read()
        # we get through when neo-battery-shutdown is running

        if "rewrite_netfiles_done" in progress:
            f = open("/usr/local/connectbox/wificonf.txt", "r")
            wifi = f.read()
            f.close()
            clientwifi =  wifi.partition("ClientIF=")[2].split("\n")[0]
            apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
            print("Client interface is ", clientwifi)
            print("AP interface is ", apwifi)

            while True:
                if not os.path.exists("/usr/local/connectbox/PauseMount"):
                    mountCheck()
                    NetworkCheck()
                    time.sleep(3)
                    x =+1 
                    if x > 2500:
                      net_stat +=1


