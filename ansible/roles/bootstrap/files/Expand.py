# Python code to expand filesystem

'''
General outline of need:

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
import re
import os

progress_file = '/usr/local/connectbox/bin/expand_progress.txt'

# Sort out how far we are in the process
file_exists = os.path.exists(progress_file)
if file_exists == False:
	do_fdisk()

else: 
    f = open(progress_file, "r")
    progress = f.read()
    f.close()
    if "resize2fs_done" not in progress:
    	do_resize2fs()
    
    else:
        exit()


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
















