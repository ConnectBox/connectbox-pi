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
    try:
         f = open(brand_file, mode="r", encoding = 'utf-8')
         brand = json.loads(f.read())
         f.close()
    except:
      version = Revision()
      if (version != "Unknown") and (version != "Error"):
        if version.find("OrangePiZero2")>=0: version  = "OZ2 "
        elif version.find("Orange") >=0: version = "OP? "
    # see if we are NEO or CM
        x = version[3:].find(" ")
        if x >= 0:
          a = version[0:x+3].rstrip()
        else:
          a = version[0:4].rstrip()

      details  = {'Brand':"Connectbox", \
        'enhancedInterfaceLogo':"", \
        'Image': 'connectbox_logo.png', \
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
      f = open(brand_file, mode='w', encoding = 'utf-8')
      f.write(json.dumps(details));
      f.close
      f = open(brand_file, mode="r", encoding = "utf-8")
      brand = json.loads(f.read())
      Brand = brand
    a = brand['usb0NoMount']
    if a == "1":
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



def do_resize2fs(rpi_platform):

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
    if (rpi_platform == True):
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


def do_fdisk(rpi_platform):

    global DEBUG
    global connectbox_scroll
    global max_partiton
    child = pexpect.spawn('fdisk /dev/mmcblk0', timeout = 10)
    try:
      i = child.expect(['Command (m for help)*', 'No such file or directory']) # the match is looking for the LAST thing that came up so we need the *
    except:
      if DEBUG: print("Exception thrown during fdisk")
      if DEBUG: print("debug info:")
      if DEBUG: print(str(child))

  # the value of i is the reference to which of the [] arguments was found
    if i==1:
        if DEBUG: print("There is no /dev/mmcblk0 partition... ")
        child.kill(0)
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
    if rpi_platform == True:
        x = 2
        while  respString.find("/dev/mmcblk0p"+str(x))>=0:
            x += 1
        x = x -1						# we will have found the last parttion then counted one more so decrement to get last partition
        max_partition = x
        p = re.compile('mmcblk[0-9]p'+str(x)+'\s*[0-9]+')        # create a regexp to get close to the sector info - CM4
    else:
        p = re.compile('mmcblk[0-9]p[0-9]\s*[0-9]+')    # create a regexp to get close to the sector info - NEO

    m = p.search(respString)    # should find "mmcblk0p1   8192" or similar, saving as object m (NEO)
                                #  or "mmcblk0p2-9   532480" or similar for CM4
    match = m.group()           # get the text of the find
    p = re.compile('\s[0-9]+')  # a new regex to find just the number from the match above
    m = p.search(match)
    startSector = m.group()
    if DEBUG: print("starting sector = ", startSector )

  # "d" for delete the partition
    child.sendline('d')

    if rpi_platform == True:    # CM4 has 2 partitions... select partition 2
        i = child.expect('Partition number')
        child.sendline(str(x))

    i = child.expect('Command (m for help)*')
# print("after delete ",child.before)

  # "n" for new partition
    child.sendline('n')
    i = child.expect('(default p):*')
# print("after new ",child.before)

  # "p" for primary partition
    child.sendline('p')
    if rpi_platform == True:    # CM4 has 2 partitions... select partition 2
        i = child.expect('default *')
        child.sendline(str(x))                 # "2" for partition number 2         i = child.expect('default 2048*')
    else:
        i = child.expect('default 1*')      # "1" for partition number 1
        child.sendline('1')
        i = child.expect('default 2048*')
# logging.info (child.before)

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

    logging.info("exiting the fdisk program... now reboot")
    f = open(progress_file, "w")
    f.write("fdisk_done")
    f.close()
    os.sync()
    # Disk is now the right size but the OS hasn't necessarily used it.
    logging.info( "PxUSBm is rebooting after fdisk changed")
    os.system('shutdown -r now')
    return()



# possible DEPRICATE... only called by NetworkCheck() (which is Depricated at the moment)

def IP_Check(b, restart):
# IP_Check will check for an IP address on the AP and optionally try an ifdown/ifup if restart = True
# this routine returns 1 if the ip address is found.

     global ifupap
     global ifdownap
     global DEBUG

     b = int(b)

     if DEBUG > 3: print("Started IP check")
     process = Popen("ifconfig", shell = False, stdout=PIPE, stderr=PIPE)       #back to checking for an IP4 addresss
     stdout, stderr = process.communicate()
     net_stats = str(stdout).split("wlan")
     a = str(net_stats[b+1][0])
     if ((len(net_stats) >= (b+1)) and (a == str(b))):
        if (not "inet" in net_stats[b+1]):
            if DEBUG: print("IP Check and no IP detected for "+net_stats[int(b)+1])
            if restart:
               process = Popen(ifdownap, shell=False, stdout=PIPE, stderr=PIPE)
               stdout, stderr = process.communicate()
               time.sleep(5)
               process = Popen(ifupap, shell=False, stdout=PIPE, stderr=PIPE)
               stdout, stderr = process.communicate()
               time.sleep(20)
               process = Popen("ifconfig", shell = False, stdout=PIPE, stderr=PIPE)       #back to checking for an IP4 addresss
               stdout, stderr = process.communicate()
               net_stats = str(stdout).split("wlan")
               if len(net_stats) >= (b+1):
                 if (not "inet" in net_stats[b+1]):
                   if DEBUG: print("did ifdown/ifup and still don't have an IP address "+net_stats[int(b)+1])
                   return(0)
                 else:
                   return(1)
               else:
                 return(0)
            else:
              return(0)
        else:
          return(1)
     else:
       logging.info("Tried checking the IP address of the AP but it was not present in ifconfig, so had to do ifup/ifdown")
       process = Popen(("ifdown wlan"+chr(b)), shell=False, stdout=PIPE, stderr=PIPE)  #We didn't have the wlan in ifconfig so we need an up/down
       stdout, stderr = process.communicate()
       process = Popen(("ifup wlan"+chr(b)), shell=False, stdout=PIPE, stderr=PIPE) 
       stdout, stderr = process.communicate()
       process = Popen("systemctl restart hostapd", shell = False, stdout=PIPE, stderr=PIPE)
       stdout, stderr = process.communicate()
       process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE) 
       stdout, stderr = process.communicate()
       net_stats = str(stdout).split("wlan")
       if len(net_stats) >= (b+1):
          if (not "inet" in net_stats[int(b)+1]):
              logging.info("After the ifup/ifdown we still didn't get an IP address")
              return(0)
          else:
              logging.info("After the ifup/ifdown we were able to get and IP address")
              return(1)
       else:
          return(0)


# possible DEPRICATE... only called by ESSID_Check (only called by NetworkCheck()... which is Depricated at the moment)

def RestartWLAN(b):
  wlanx = "wlan"+str(b)

  # normally a wlan restart can be done by restart hostapd, 
  #  restart dnsmasq, ifdown, if up sequence

  cmd = "ifdown "+wlanx
  rv = subprocess.call(cmd, shell=True)
  cmd = "ifup "+wlanx
  rv = subprocess.call(cmd, shell=True)
  time.sleep(5)
  if check_iwconfig(b) == 1:
    return(1)   # wlanx is up 

# else we continue
  cmd = "systemctl restart hostapd"
  rv = subprocess.call(cmd, shell=True)
  cmd = "systemctl restart dnsmasq"
  rv = subprocess.call(cmd, shell=True)
  time.sleep(5)
  if check_iwconfig(b) == 1:
      return(1)   # wlanx is up 
#    else:
#     print("WLAN not up... we need to run hostapd")
#      cmd = "systemctl restart hostapd"
#      rv = subprocess.call(cmd, shell=True)
#      print("hostpad... Returned value ->", rv)
#      return(rv)
  else:
    return(0)  #Error in length or reply compared to expectation


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
    wlanx_flags = rvs[1].split("Mode:Master")
    if (len(wlanx_flags)) > 1:
      # we are up
      return(1)
    else:
      return 0  




# possible DEPRICATE... only called by NetworkCheck() (which is Depricated at the moment)

def ESSID_Check(b, restart):
# this routine ESSID_check will look to see if there is an ESSID assigned to the AP
# you pass this routine the wlan character and  if you want to attempt a restart of hostapd if no ESSID a restart value of True
# it will return a 1 if the ESSID is present and 0 otherwise
    global first_time
    global DEBUG
    global SSID

    if DEBUG > 3: print("Started ESSID check")
    process = Popen("iwconfig", shell=False, stdout=PIPE, stderr=PIPE)            # now well check for an ip address on the AP
    stdout, stderr = process.communicate()
    net_stats = str(stdout).split("wlan")                                        #split up iwconfig by wlan so the first wlan status is in net_stats[1]

    #if we didn't find a " or no ESSID then we will try a down/up sequence for the wlan
    if ((len(net_stats) ==1) or (not "IEEE 802.11gn  ESSID:" in net_stats[int(b)+1])):
      logging.info("did iwconfig but no ESSID present "+net_stats[int(b)+1])
      if restart:
        RestartWLAN(b)
      return (0)      # we have restarted but have no info

    # else, we have one or more WLANs... check to see if the ESSID and SSID match
    elif(len(net_stats) != 1):
      x = net_stats[int(b)+1].find("ESSID:")
      a = net_stats[int(b)+1][(x+6):].lstrip()      #get the starting of the SSID but clear preceeding blanks
      y = a.find(" ")                               #find the real SSID
      if ( x >= 0 and y >= 0 ):
          a = a[0:(y)] 
          a = a.replace('"','')                     #get the substring which is the Brand part only of the ESSID for this device
          logging.info("The ESSID is: "+a)
      else:
          a = '""'
          logging.info('The ESSID is: ""')

# check if ESSID and SSID match
      if not((SSID in a) and (a != '""')):         #We didn't find the right SSID in ESSID
          first_time = True
          logging.info("were setting firstime true to restart hostapd and dnsmasq as ESSID and SSID didn't match")
# we have a valid ESSID / SSID match... no need to do anything.
      else:
          first_time = False
          return(1)
      if first_time:
        RestartWLAN(b)
        first_time = False
        return(0)


def dbCheck():
       process = Popen("systemctl status mysql", shell = False, stdout=PIPE, stderr=PIPE)
       stdout, stderr = process.communicate()
       if stdout.find("active (running) since")>=0:
          return(0)
       else:
          process = Popen("systemctl restart mysql", shell = False, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          process = Popen("systemctl status mysql", shell = False, stdout=PIPE, stderr=PIPE)
          stdout, stderr = process.communicate()
          if stdout.find("active (running) since")>= 0:
              return(0)
       return(1)



# possible DEPRICATE... only called by NetworkCheck() (which is Depricated at the moment)

def check_flags(b, restart):
# check flags will check for run status of the interface flags.  EG: 4099 not running vs 4163 which is running

     global ifupap
     global ifdownap
     global DEBUG

     b = int(b)

     if DEBUG > 3: print("Started check_flags")
     process = Popen("ifconfig", shell = False, stdout=PIPE, stderr=PIPE)       #back to checking for an IP4 addresss
     stdout, stderr = process.communicate()
     net_stats = str(stdout).split("wlan")
     if (len(net_stats) <= b+1):
        if (not "flag=4163" in net_stats[int(b)+1]):
          logging.info("did ifconfig but no flag=4163 present "+net_stats[int(b)+1])
          if DEBUG: print("did ifconfig but no flag=4163 presently")
          if restart:
            if (RestartWLAN(b)):
              process = Popen("iwconfig", shell = False, stdout = PIPE, stderr=PIPE)
              stdout, stderr = process.communicate()
              net_stats = str(stdout).split("wlan")
              if (len(net_stats) <= (b+1)):
                if (not "flag=4163" in net_stats[int(b)+1]):
                  #we restarted and rechecked and don't have a run flag
                  return (0)      # we have restarted but have no run flag
                else:
                  return(1)       # were up and running
              else:
                return(0)         # our response didn't match our expectations of # wlan ports
            else:
              return(0)           #we had an error on Restart and not running
          return(0)
        return(1)                 #were up and running 
     return(0)                   #our response weas different than the port expectations
 

# possible DEPRICATE... was in main()... commented out

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
  global first_time
  global DEBUG

  if DEBUG > 3: print("Started Network Check")
  file_exists=True

  try:
    file_exists = os.path.exists("/var/run/network/*.pid")
  except:
    file_exists = False
  if file_exists == True:
    process = os.popen("ls /var/run/network/*.pid")
    net_stats = process.read()
    process.close()
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
    logging.info("hostapd maskded will unmask it")
    process = os.popen("systemctl unmask hostapd.service")
    net_stats = process.read()
    time.sleep(5)
    process.close()
    if net_stats.find("Removed")>=0:                                      # if for some reason hostapd is removed enable it
        logging.info("Removed the mask on hostapd now we can enable it")
        process = os.popen("systemctl enable hostapd.service")
        net_stats = process.read()
        time.sleep(5)
        process.close()
        if net_stats.find("enabled hostapd")>=0:                          # if hostapd is enabled make sure it  is started
            logging.info("Restarting hostapd service")
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
                if DEBUG: logging.info ("succeeded in unmasking, enabling and starting hostapd")
        else:
              logging.info("Failed to enable hostapd after unmasking")
              hostapd_running=False
    else:
        logging.info("Failed to unmask hostapd")
        hostapd_running=False
  else:
    if net_stats.find("Loaded: loaded") >= 0:                            #if hostapd is loaded: loaded it may not be running
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

  b = int(apwifi[len(apwifi)-1])                                     # b contains the AP wifi character (0, 1, 2, .....)
  if clientwifi=="":
    if str(b) >= "1":                                                   # if b > 0 then the c is lower
      c = chr(int(b)-1+ord("0"))
    else:
      c = chr(int(b)+1+ord("0"))
  else:
    c = clientwifi[(len(clientwifi)-1):]                                 # c contains the client wifi character (0, 1, 2, ...) if there was none then its one higher than AP

  #check the ESSID and if its not there try to restart the hostapd/dnsmasq
  if not hostapd_running:
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
           if (check_flags(b,True)):
              logging.info("have PI version with no extra WIFI modules and no IP address for AP or runn flag not set")
           else:
              logging.info("have a PI version and now have a good run flag but still no IP")
         else:
           valid_IP=True
           if (not check_flags(b,True)):
             valid_ESSID=False
             if DEBUG: print("weve done our best to bring up the AP since this is a PI with no other WIFI modules but not running flag")
             logging.info("weve done our best to bring up the AP since this is  a PI with no other WIFI modules")
           else:
             valid_ESSID=True   # since we have a running status we assume we have the right ESSID for this pi
      else:
        if (not IP_Check(b, True)):					# now well check for an ip address on the AP
          valid_IP=False
          if (not ESSID_Check(b, True)):				# Ok so we couldn't get the interface up but now we reset hostapd so lets try an up/downn again
            if check_flags(b,False):
                valid_ESSID=False 
                if DEBUG: print("We cant get an ESSID and we didn't get an IP.... what to do?")
                logging.info("We can't get an ESSID and we didn't get and IP..... what to do?")
            else:
                if (PI_stat):
                    valid_ESSID=True          # OK so we are a Pi it will never have a valide ESSID but were running so we assume were ok
                    if DEBUG: print("We are a pi and we are running so we assume were ok")
                    logging.info("We are a pi and we are running so we assume were ok")
                else:
                    valid_ESSID=False
                    if DEBUG: print("We are unable to get a valid_ESSID")
                    logging.info("We are unable to get a valid_ESSIDF")
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
          if (not PI_stat):
            if valid_ESSID==False:
                if (not ESSID_Check(b, True)):
                    valid_ESSID=False
                    stop_hostapd=True						#we have tried three times so were going to  hope were up.
                    if DEBUG: print("Weve given up we tried three times and cant get a valid ESSID")
                    logging.info("weve given up since we have tried 3 times and cant get and ESSID")
                else:
                    valid_ESSID=True
                    if DEBUG: print("we think were ok since got an ESSID on our last try")
                    logging.info("we think were ok since we got an ESSID on our last try")
          else:
            if (not check_flags(b,True)):
                valid_ESSID=False
                stop_hostapd=True               #we have tried three times so were going to hope were up
                if DEBUG: print("we think were ok since got an ESSID on our last try")
                logging.info("we think were ok since we got an ESSID on our last try")
            else: 
                valid_ESSID=True                #Since were a pi we know we dont'get an ESSID but were running flag true.  We think were up
                if DEBUG: print("we think were ok since were a pi and know we won't get an ESSID but were running on our last try")
                logging.info("we think were ok since were a pi and know we won't get an ESSID but were running on our last try")
    else:
      valid_ESSID=True 
      if (not IP_Check(b, True)):					#Check to make sure we have an ip now that we have an ESSID
         valid_IP=False
         if DEBUG: print("We have an essid but can't get an IP....")
         logging.info("We have an ESSID but we couldn't get an IP address... what to do?")
      else: valid_IP=True						#We got a valid ESSID the first time and got a valid IP
  else:
    if (not PI_stat):
      if (not ESSID_Check(b,False)):
          valid_ESSID=False
      else:
          valid_ESSID=True									#were here because were a PI and have not other WIFI's so just check the IP address
    else:
      if (not check_flags(b,False)):
          valid_ESSID=False
      else:
          valid_ESSID=True                  #were a pi so we knonw we wont get an ESSID but we are up and running by flags
    if (not IP_Check(b,True)):
      valid_IP=False
    else:
      valid_IP=True

  if valid_IP and valid_ESSID and hostapd_running and network_running and DEBUG: print("AP up and running ok")
  else:
    if DEBUG: print("Not everything is clean: IP, ESSID, hostapd, network, stop_hostapd ",valid_IP, valid_ESSID, hostapd_running, network_running, stop_hostapd)
  res = os.popen("ls /sys/class/net")
  SysNetworks = res.read().split()
  res.close()
  for netx in SysNetworks:                                                # Look at each interface
    if (netx != ""):
      try:
          process = os.popen("cat /sys/class/net/"+netx+"/operstate")     #check the operational state of all interfaces
          net_stats = process.read()
          process.close()
          if net_stats.find("down") >= 0 :                                # if its down lets try to raise it
            if areadyconf.find(netx) < 0 :                                # Were checking to see if we should leave this network alone
                cmd = "ifup "+netx
                process = Popen([cmd],shell=False, stdout=PIPE, stderr=PIPE)
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
                process = os.popen("cat /sys/class/net/"+netx+"/operstate")
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
                    else:
                      process = os.popen("ifup " + netx)
                      time.sleep(5)
                      net_stat= process.read()
                      process.close()
                      logging.info("re-started the interface "+netx)
            except:
                  logging.info("Interface "+netx+" needs to be configured")
    logging.info("stopped all interfaces as much as possible")   
#restart networking
    try:
        res = os.popen("systemctl restart networking.service")
        res.close()
    except:
        logging.info("networking.service has configuration issues")
    process = os.popen("systemctl status networking.service")
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

  global DEBUG

  if DEBUG > 3: print("Started Revision test")
  revision = ""
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if "Revision" in line:
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
        if "rtl88" in netwk[1][1]:                                  #if we have an rtl on the second wlan we will use it for AP
            AP = netwk[1][0]                                    #interface 2 has the rtl and will be AP
            CI = netwk[0][0]                                    #interface 1 is on board or other andd will be the client side for network

        logging.info("AP will be: wlan"+AP+" ethernet facing is: wlan"+CI)
        if len(netwk) >=3:
            logging.info("we have more interfaces so they must be manually managed") # if we have more than 2 interfaces then they must be manually managed. 
# --- no files changed (more than 2 interfaces... how to handle??) ---
            return(0)

    else:                                                           # we don't have even 1 interface
        logging.info("We have no wlan interfaces we can't function this way, rebooting to try to find the device")
# --- no files changed (no interfaces... maybe we missed one... how to handle??) ---
        return(0)


# the following statement will fail because "AP" should be "wlan"+AP
#  so it hasn't been doing anything in the past (and hasn't been missed)
#  We will comment out this section but leave it in place incase it later proves useful
#    res = os.popen("ip link show "+AP).read()
#    x = res.find("permaddr:")
#    if ( x > 0 ):
#        addr = res[(x+9):(x+26)]
#    else:
#         x = res.find("link/ether")
#         if (x > 0):
#             addr = res[(x+11):(x+27)]
#         else:
#             addr = 0
#    if (addr > 0):
#    # now that we have the AP file lets setup the /etc/systemd/network/10-wlanX.link file
#         d = "/etc/systemd/network/10-"+AP+".link"
#         try:
#             f = open(d,'r')
#             f.close()
#         except:
#             f = open(d, "w")
#             f.write("\n[Match]\nMACAddress="+dap+"\n[Link]\nName="+AP+"\nMACAddressPolicy=random\n")
#             f.close()
#             os.sync()
#             res=os.popen("update-initramfs -u")
#             os.sync()

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
#  Might speed this up if we selectively address CI based on files_changed result...

    if level == 2:                  # do the full up/down package (these take some time... especially CI)
      os.system("ifdown wlan"+CI)
      os.system("ifup wlan"+CI)

# the following go pretty quick and may/should bring us up if the wlans didn't trade during boot
    os.system("ifdown wlan"+AP)
    os.system("ifup wlan"+AP)
    os.system("ifconfig wlan"+AP+" down")
    os.system("ifconfig wlan"+AP+" up")

    os.system("ifdown eth0")
    os.system("ifup eth0")
    os.system("ifconfig eth0 down")
    os.system("ifconfig eth0 up")

    os.system("ifconfig wlan"+CI+" down")
    os.system("ifconfig wlan"+CI+" up")



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

    logging.debug("Entering fix files")

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
        logging.info("Skipped file reconfiguration as the configuration is the same")
#        os.system("ifup wlan"+a)   # restart wlan ... other restarts needed??n

# if wificonfig.txt agrees with info from lshw we can continue without changing anything
        return(0)          

# if NOT, we cook the files and will restart the services with 
    res = os.system("systemctl stop networking.service")
    res = os.system("systemctl stop hostapd")
    res = os.system("systemctl stop dnsmasq")
    res = os.system("systemctl stop dhcpcd")

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

    os.system("systemctl daemon-reload")             #we reload all the daemons since we changed the config.
    time.sleep(5)

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

def check_eth0():
  process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
  stdout, stderr = process.communicate()
  net_stats = str(stdout).split("eth0")   # look for eth0 in ifconfig output
  if (len(net_stats)==1):     # eth0 not found... restart eth0
    os.system("ifdown eth0")
    os.system("ifup eth0")
    os.system("ifconfig eth0 down")
    os.system("ifconfig eth0 up")
  return(0)  


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

    DEBUG = 4
    SSID=""
    connectbox_scroll=False
    first_time=True
    stop_hostapd=False
    areadyconf= ""

    version = Revision()                    # Get the version of hardware were running on
    if (version != "Unknown") and (version != "Error"):
      if version.find("OrangePiZero2")>=0: version  = "OZ2 "
      elif version.find("Orange") >=0: version = "OP? "
    # see if we are NEO or CM
      x = version[3:].find(" ")
      if x >= 0:
          a = version[0:x+3].rstrip()
      else:
          a = version[0:4].rstrip()


    logging.info("PxUSBm Starting revision is "+version)
    try: 
      f = open(brand_file, mode="r", encoding='utf-8')
      brand = json.loads( f.read() )
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
    brand = json.loads(f.read())
    Brand = brand
    f.close

#    NoMountUSB = brand.find('"usb0NoMount:1')
    NoMountUSB = brand.get("usb0NoMount") == 1   # Note: brand is type dict, so no "find" method
    rpi_platform=False
    PI_stat = False
    OP_stat = False


# -- sort out the SSID

    if (version != "Unknown") and (version != "Error"):
      logging.info("Major type: "+a)
      if brand["Device_type"].find(a)<=0:                    # Make sure the brand file is what we expect as were on this hardware.
        f = open(brand_file, mode="w", encoding = 'utf-8')
        brand["Device_type"] = '"'+a+'"'
        if a.find("CM")>0 :
          brand["lcd_pages_multi_bat"] = 1
        else:
          brand["lcd_pages_multi_bat"] = 0
        f.write(json.dumps(brand))
        f.close()
        os.sync()
        SSID = brand["Brand"]
    else:
        SSID = "ABC"
    x=SSID.find('"')                          #Remove all the quotation marks around the  SSID
    while ( x >= 0 and len(SSID)>0):
      SSID = SSID.replace('"','')
      x=SSID.find('"')

    logging.info("SSID from file is now: "+SSID)

    if 'CM' in brand["Device_type"]:             #Now we determine what brand to work with
        rpi_platform=True
        PI_stat=True
        OP_stat=False

    if "PI" in brand["Device_type"]:
        rpi_platform=True
        PI_stat=True
        OP_stat = False

    if "NEO" in brand["Device_type"]:
        rpi_platform=False
        PI_stat=False
        OP_stat=False

    if "OZ2" in brand["Device_type"]:
        rpi_platform = False
        PI_stat=False
        OP_stat =True
    if DEBUG > 3: print("Our device is type RPI platform:"+str(rpi_platform)+" and PI itself:"+str(PI_stat)+" and  Orange PI:"+str(OP_stat))
    net_stat = 1

    while (net_stat == 1):

        # Sort out how far we are in the partition expansion process
        file_exists = os.path.exists(progress_file)
        if file_exists == False:
            do_fdisk(rpi_platform)             # this ends in reboot() so won't return
            continue
        else: 
            f = open(progress_file, "r")
            progress = f.read()
            f.close()
            if "fdisk_done" in progress:
                do_resize2fs(rpi_platform)     # this ends in reboot() so won't return
                continue

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

        getNetworkClass(1)  # Note: calls fixfiles() if required... the (1) signals minimal ifconfig down/up

        x = 95    # give time for network to come up before trying to fix it

        while (x == x):                         # main loop that we live in for life of running
          if (NoMountUSB <= 0):
             if DEBUG > 3: print("PxUSBm Going to start the mount Check")
             mountCheck()                   # Do a usb check to see if we have any inserted or removed.
             if connectbox_scroll: dbCheck()

          if ((x % 3)==0):
          # check to see if AP is still active
            AP = get_AP()
            AP_up = check_iwconfig(AP)  # returns 1 if up
            if (not AP_up):
              getNetworkClass(1)       # try to fix the problem (shouldn't get here normally)

            check_eth0()      # make sure eth0 is up  
   
          if ((x % 10)==0):
            if DEBUG > 3: print("PxUSBm Going to do a Network check"+time.asctime())

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
            filedata=f.read()
            f.close()             
            NoMountUSB = str(filedata).find('usb0NoMount": 1')

# loop            
          x += 1
          time.sleep(3)


