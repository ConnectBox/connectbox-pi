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
import logging.handlers
import re
import os
from subprocess import Popen, PIPE
import subprocess
import shutil
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

# Drive letters (e.g. 'b') whose file system is on the whole disk (/dev/sdb)
# instead of the first partition (/dev/sdb1).  Linux users often format a USB
# stick with no partition table (mkfs.ext4 /dev/sdb).
global whole_disk
whole_disk = set()

# Devices (e.g. 'sdb1') that failed to mount.  They are not retried on every
# 3 s poll; the entry is dropped when the device is unplugged.
global failed_mounts
failed_mounts = set()

# File systems that store Unix permissions (Linux formats).  They reject the
# FAT-only utf8 mount option and are not checked with dosfsck/ntfsfix.
POSIX_FILESYSTEMS = ('ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'f2fs')

# Longest a file-system check before a mount may take.  PxUSBm waits for the
# check (and does nothing else meanwhile, Wi-Fi watching included); a full
# dosfsck of a 64 GB FAT32 card took over 7 minutes on a NanoPi NEO
# (2026-10-29).  After the limit the check is stopped and the key mounted.
FS_CHECK_SECS = 120

# Front-panel message while a check runs ("Checking USB"): refreshed every few
# seconds, so the hat service shows it while it is fresh.  It is not the
# indexing status file (/tmp/creating_menus.txt), whose removal makes the panel
# show its "done" checkmark.
USB_CHECK_STATUS = "/tmp/connectbox-usbcheck.txt"
USB_CHECK_TEXT = "Checking USB\nplease wait"

global net_stat
net_stat = 1

global Brand

global connectbox_scroll

global max_partition
max_partiton = 0


def attiny_present(device):
  """
  True if the front panel's ATtiny battery controller answers at I2C address
  0x14: bus 10 on a Compute Module (CM*), bus 1 on another Raspberry Pi.
  Other boards have no ATtiny.  Uses smbus2 (installed by the build); False
  if it is missing or the read fails.
  """
  if device.startswith("CM"):
    bus = 10
  elif device.startswith("PI") or device.startswith("Pi") or device.startswith("RPi"):
    bus = 1
  else:
    return False
  try:
    import smbus2
    with smbus2.SMBus(bus) as b:
      b.read_byte(0x14)
    return True
  except Exception:
    return False


def write_brand_file(brand):
    """
    Write brand.j2 whole to a temporary file and rename it into place, so
    the hat service and connectbox-manage never read it half written (the
    hat service crashed reading an empty brand.j2).  Keeps owner and mode.
    """
    tmp = brand_file + ".tmp." + str(os.getpid())
    with open(tmp, mode="w", encoding='utf-8') as f:
        f.write(json.dumps(brand))
        f.flush()
        os.fsync(f.fileno())
    try:
        st = os.stat(brand_file)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.chown(tmp, st.st_uid, st.st_gid)
    except OSError:
        pass
    os.replace(tmp, brand_file)


def mounted_device(target):
    """
    The device mounted at target according to /proc/mounts ('' if none).
    When mounts are stacked on the same folder the last one is the one in use,
    so the last entry is returned (the first one made PxUSBm "forget" a key
    mounted on top of a dead mount, every 3 s, 2026-10-29).
    """
    found = ''
    try:
        with open('/proc/mounts', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if len(parts) > 1 and parts[1].replace('\\040', ' ') == target:
                    found = os.path.realpath(parts[0])
    except OSError:
        pass
    return found


def usb_slot_mounts():
    """(device, mount point) for every /media/usb0../media/usb9 mount, in /proc/mounts order."""
    out = []
    try:
        with open('/proc/mounts', encoding='utf-8') as f:
            for line in f:
                parts = line.split()
                if len(parts) > 1 and re.fullmatch(r'/media/usb[0-9]', parts[1]):
                    out.append((parts[0], parts[1]))
    except OSError:
        pass
    return out


def release_usb_slots():
    """
    At start-up, lazily unmount every /media/usb0..9 mount.  PxUSBm starts with
    empty mount tables, so a key mounted by an earlier PxUSBm (before a restart)
    was never adopted: when it was pulled out its mount stayed behind, dead,
    and the next key was mounted on top of it (2026-10-29).  The following
    mount checks mount the keys that are present again, with the usual check
    and indexing.  /media/usb11 (the front panel's copy mount) is left alone.
    """
    for _ in range(20):
        mounts = usb_slot_mounts()
        if not mounts:
            return
        dev, target = mounts[-1]
        logger.info("Start-up: releasing " + dev + " mounted at " + target + " before PxUSBm started, time is " + time.asctime())
        if target == "/media/usb0":
            try:
                os.remove('/tmp/.usb0_indexed')     # index whatever key is mounted there next
            except OSError:
                pass
        if os.system("umount -l " + target + " 2>/dev/null") != 0:
            return


def clear_dead_mounts(target):
    """Lazily unmount mounts at target whose device no longer exists (so mounts never stack)."""
    for _ in range(10):
        dev = mounted_device(target)
        if not dev or os.path.exists(dev):
            return
        logger.info("Removing dead mount of " + dev + " at " + target + ", time is " + time.asctime())
        if os.system("umount -l " + target + " 2>/dev/null") != 0:
            return


def usb_device_name(letter):
    """
    Return the block device name mounted for a drive letter: 'sdb' when the
    file system is on the whole disk, otherwise the first partition 'sdb1'.
    """
    return 'sd' + letter + ('' if letter in whole_disk else '1')


def fat_needs_check(dev):
    """
    True when the FAT volume on /dev/<dev> should be checked before mounting:
    it was not unmounted cleanly, it records a disk I/O error, or its boot
    sector cannot be read.  Both places dosfsck looks are read: Windows keeps
    two flags in FAT entry 1 (bit 1 = clean shutdown, next bit 1 = no I/O
    error), Linux sets bit 0 of the boot sector's state byte while the volume
    is mounted.  So a key pulled out without unmounting is checked.  FAT12
    has no flags and is not checked.
    """
    import struct
    try:
        with open('/dev/' + dev, 'rb') as f:
            bs = f.read(512)
            if len(bs) < 512 or bs[510:512] != b'\x55\xaa':
                return True
            bps, spc, res, nfats = struct.unpack_from('<HBHB', bs, 11)
            root_ents, tot16 = struct.unpack_from('<HH', bs, 17)
            fatsz16 = struct.unpack_from('<H', bs, 22)[0]
            tot32, fatsz32 = struct.unpack_from('<II', bs, 32)
            if bps not in (512, 1024, 2048, 4096) or spc == 0 or nfats == 0:
                return True
            fatsz = fatsz16 or fatsz32
            total = tot16 or tot32
            root_secs = (root_ents * 32 + bps - 1) // bps
            clusters = (total - res - nfats * fatsz - root_secs) // spc
            f.seek(res * bps)
            fat = f.read(8)
        if clusters < 4085:                       # FAT12
            return False
        if clusters < 65525:                      # FAT16
            e1 = struct.unpack_from('<H', fat, 2)[0]
            return (e1 & 0xC000) != 0xC000 or bool(bs[0x25] & 0x01)
        e1 = struct.unpack_from('<I', fat, 4)[0]  # FAT32
        return (e1 & 0x0C000000) != 0x0C000000 or bool(bs[0x41] & 0x01)
    except Exception:
        return True


def show_usb_check(on=True):
    """Write (refresh) or remove the front panel's "Checking USB" message."""
    try:
        if on:
            with open(USB_CHECK_STATUS, "w", encoding="utf-8") as f:
                f.write(USB_CHECK_TEXT)
        elif os.path.exists(USB_CHECK_STATUS):
            os.remove(USB_CHECK_STATUS)
    except OSError:
        pass


def run_fs_check(cmd):
    """
    Run a file-system check (argument list) with the FS_CHECK_SECS limit,
    showing "Checking USB" on the front panel meanwhile; its output goes to
    the journal as before.  Returns the exit code, or None when it was stopped
    at the limit or could not run.  Stopping dosfsck early writes nothing:
    without -w it keeps its repairs and writes them at the end.
    """
    try:
        proc = subprocess.Popen(cmd)
    except Exception as e:
        logger.info("Could not run " + " ".join(cmd) + ": " + str(e))
        return None
    deadline = time.time() + FS_CHECK_SECS
    while True:
        show_usb_check(True)
        try:
            return proc.wait(timeout=max(0.1, min(5, deadline - time.time())))
        except subprocess.TimeoutExpired:
            if time.time() >= deadline:
                proc.kill()
                proc.wait()
                logger.info(" ".join(cmd) + " stopped after " + str(FS_CHECK_SECS) + " s; mounting without it, time is " + time.asctime())
                return None


def get_fstype(dev):
    """
    Return the file system type of /dev/<dev> (e.g. 'vfat', 'ext4'), or '' if
    the device has none.  lsblk reads udev's database, so this does no disk I/O.
    """
    try:
        out = subprocess.run(['lsblk', '-dno', 'FSTYPE', '/dev/' + dev],
                             capture_output=True, text=True, timeout=10).stdout
        return out.strip()
    except Exception:
        return ''


def match_usb_device(line, listing):
    """
    Return a regex match naming the USB device on one lsblk line, or None.

    Matches the first partition (sdX1, the usual case) or a whole disk (sdX)
    that carries a file system itself and has no partitions.  Disk lines start
    at column 0 in lsblk's tree output; partition lines are indented.  `listing`
    is the full lsblk output, used to skip disks that have partitions without
    running lsblk again for them.
    """
    e = re.search('sd[a-z]1', line)
    if e:
        return e
    e = re.match(r'sd[a-z]\b', line)
    if e and ' disk' in line and not re.search(e.group() + r'\d', listing):
        if get_fstype(e.group()) != '':
            return e
    return None


# Kiwix library that mmiLoader fills with the USB's ZIM files (see mmiLoader.py)
KIWIX_LIBRARY = "/var/lib/connectbox/kiwix/library.xml"
EMPTY_KIWIX_LIBRARY = '<?xml version="1.0" encoding="UTF-8"?>\n<library version="20110515">\n</library>\n'


def clear_kiwix_library():
    """
    Empty the Kiwix library when usb0 is removed, so kiwix-serve (which
    re-reads it within ~2 s) stops listing ZIM files that are no longer there.
    Does nothing if Kiwix has never been set up.
    """
    if not os.path.isfile(KIWIX_LIBRARY):
        return
    try:
        with open(KIWIX_LIBRARY, "w", encoding="utf-8") as f:
            f.write(EMPTY_KIWIX_LIBRARY)
    except OSError as e:
        logger.info("Could not clear the Kiwix library: " + str(e))


def start_content_loader():
    """
    Start mmiLoader.py to index the USB mounted at /media/usb0.

    Runs in a transient systemd unit (connectbox-loader) so indexing continues
    in the background while this daemon keeps polling.  --remain-after-exit
    keeps the unit loaded after mmiLoader finishes, so the previous run must be
    stopped (which unloads it) before systemd-run can reuse the name; otherwise
    it fails with "Unit connectbox-loader.service already exists" and nothing
    is indexed.  `systemctl stop` already waits for the stop to finish.  (Do not
    add --wait: systemd 247 on Debian 11 rejects it for stop and stops nothing.)
    """
    logger.info("Starting mmiLoader content load, time is " + time.asctime())
    os.system("systemctl stop connectbox-loader.service 2>/dev/null; systemctl reset-failed connectbox-loader.service 2>/dev/null")
    # Belt and braces: give systemd up to 5 s to unload the old unit
    for _ in range(10):
        state = subprocess.run(['systemctl', 'show', '-p', 'LoadState', '--value', 'connectbox-loader.service'],
                               capture_output=True, text=True).stdout.strip()
        if state != 'loaded':
            break
        time.sleep(0.5)
    if os.system("/usr/bin/systemd-run --unit=connectbox-loader --description='ConnectBox Content Loader' --remain-after-exit /usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py") != 0:
        logger.info("Could not start mmiLoader (systemd-run failed), time is " + time.asctime())


# The box's own content: /media/usb0/content on the SD card, copied there from
# a key with the front-panel "copy from USB".  A key plugged in is mounted on
# top of /media/usb0 and its content is shown instead; when it is pulled out
# (or the box starts without a key) the box's own content is indexed again.
INTERNAL_CONTENT = "/media/usb0/content"
INTERNAL_INDEXED = "/tmp/.internal_indexed"      # set once the own content has been indexed
INTERNAL_STARTUP_WAIT = 20                       # s after start-up, to let a plugged-in key appear
pxusbm_started = time.time()


def check_internal_content():
    """
    Index the box's own content when no USB key is mounted at /media/usb0.

    Called after every mountCheck().  Runs the loader once (INTERNAL_INDEXED
    stops it repeating every poll); mountCheck() removes that marker when a key
    is pulled out of usb0, so the content is indexed again then.  At start-up
    it waits INTERNAL_STARTUP_WAIT seconds so that a key that is plugged in is
    mounted (and indexed) instead.  With no content of its own the box keeps
    the empty menus left by mmiLoader --clear.
    """
    if os.path.isfile(INTERNAL_INDEXED) or os.path.ismount("/media/usb0"):
        return
    if time.time() - pxusbm_started < INTERNAL_STARTUP_WAIT:
        return
    try:
        has_content = os.path.isdir(INTERNAL_CONTENT) and any(
            not name.startswith('.') for name in os.listdir(INTERNAL_CONTENT))
    except OSError:
        has_content = False
    if has_content:
        logger.info("No USB at /media/usb0: indexing the box's own content, time is " + time.asctime())
        start_content_loader()
    try:
        open(INTERNAL_INDEXED, 'w').close()
    except OSError:
        pass


def mountCheck():
    """
    Poll the system for USB drive insertion and removal events, then mount or unmount
    drives as appropriate.

    This is the central USB-management function called on every iteration of the main
    daemon loop.  It performs three conceptual passes over the state of the system:

    Pass 1 — detect removals:
        Walk the ``mnt[]`` / ``loc[]`` parallel arrays.  For each slot that previously
        held a mounted drive, check whether ``lsblk`` still shows the device.  If the
        device has gone away, issue ``umount``, delete the mount-point directory (for
        usb1+), remove the ``/tmp/.usb0_indexed`` sentinel (for usb0), and clear the
        slot in both arrays.

    Pass 2 — detect new insertions:
        Re-parse the ``lsblk`` output line by line looking for ``sdX1`` devices that
        are not yet mounted.  For each new device, pick the lowest-numbered free
        ``/media/usbN`` slot, run ``dosfsck``/``ntfsfix`` for filesystem integrity,
        then mount with ``noatime,nodev,nosuid,utf8`` flags.  Kernel >=5.15 uses
        ``utf8=`` directly; older kernels need ``iocharset=utf8``.  On a successful
        usb0 mount, trigger the upgrade script.

    Pass 3 — compact the mount table:
        After additions and removals the ``mnt[]``/``loc[]`` arrays may have holes.
        This pass bubbles all occupied slots to the front so the arrays remain
        contiguous and ``total`` is an accurate count.

    SSH-enabler side-effect:
        After each pass 1 iteration the function also evaluates whether
        ``/media/usb0/.connectbox/enable-ssh`` exists and starts sshd if so.  This
        runs unconditionally so that a newly inserted key can enable SSH without
        waiting for the next full cycle.

    Globals used:
        mnt (list): Parallel array mapping slot index -> ord() of the sdX drive letter
                    (e.g. ord('a') for /dev/sda1).  -1 means slot is empty.
        loc (list): Parallel array mapping slot index -> ord() of the usb mount number
                    (e.g. ord('0') for /media/usb0).  -1 means slot is empty.
        total (int): Count of currently mounted drives after this call completes.
        Brand (dict): Parsed brand.j2 configuration; ``usb0NoMount`` key suppresses
                      all mounting when set to "1".
        DEBUG (int): Verbosity level; 1=network, 2=mount summary, 3=mount detail.

    Returns:
        None
    """
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
      logger.info("no mount set")
      print("no mount set")
      return
    total = 0

    # --- Pass 1: Detect USB removals ---
    # Snapshot the current block-device tree once with lsblk.  We then walk every
    # occupied slot in mnt[] and check whether the corresponding sdX1 device still
    # appears in that snapshot.  If it has disappeared the drive was physically
    # removed (or ejected by udev), so we issue umount, clean up the mount-point
    # directory, and free the slot.
    # We use lsblk rather than /proc/mounts because lsblk reflects kernel block-
    # device state; a device can vanish from the kernel before /proc/mounts is
    # updated, which would cause umount to return non-zero.  We handle that case
    # (res != 0) gracefully by logging a warning and still clearing the slot.
    j = 0                   #mount iterator looking for unmounted devices
    process = os.popen('lsblk')
    b = process.read()
    process.close()
    # Forget failed mounts for devices that have been unplugged, so the same
    # stick is retried when it is plugged back in.
    for dev in list(failed_mounts):
      if dev not in b:
        failed_mounts.discard(dev)
    while (j < 11):
      if DEBUG > 2: print("loop 1, unmount",j)
      if (mnt[j] >= 0):
        if not (usb_device_name(chr(mnt[j])) in b):
          if loc[j] == ord('0'):
            # Stop indexing before the mount goes away under mmiLoader, stop
            # Kiwix offering the removed USB's ZIM files, and empty the menus
            # (built on the device at insert) so no cards point at missing files
            os.system("systemctl stop connectbox-loader.service 2>/dev/null")
            clear_kiwix_library()
            os.system("/usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py --clear >/tmp/mmiLoader_clear.log 2>&1")
          # Unmount by mount point, lazily: the /dev node is already gone, so
          # `umount /dev/sdX1` would fail and leave a stale mount behind.
          c = 'umount -l /media/usb' + chr(loc[j])
          print("unmount /dev/"+usb_device_name(chr(mnt[j])))
          if DEBUG > 2: print("No longer present "+usb_device_name(chr(mnt[j]))+" so well "+c)
          if DEBUG > 2: print("the value of b is"+b)
          res = os.system(c)
          if DEBUG > 2: print("completed "+c)
          if res == 0:
            logger.info("Unmounted USB drive at "+c+" time is " + time.asctime())
            if loc[j] > ord('0'):
               process = os.popen('rmdir /media/usb'+chr(loc[j]))
               process.close()
               print("Deleted the directory /media/usb",chr(loc[j]))
            else:     #We just unmounted usb0 so we need to rerun the enhanced interfaceUSB loader
                      # Run these functions on mount -- added 20211111
              # Enhanced Content Load
              logger.info("Start load content for menu's time is:" + time.asctime())
              try:
                  os.system("rm /usr/local/connectbox/complex_dir")
              except:
                  pass
              logger.info("Finished load content for menu's, time is" + time.asctime())
              try:
                  os.system("rm /usr/local/connectbox/complex_dir")
              except:
                  pass
          else:
            logger.info("Umount returned non-zero (already unmounted?) for "+c)
          # Always clear sentinel and table when device is gone from lsblk,
          # regardless of whether our umount call succeeded
          if loc[j] == ord('0'):
              try:
                  os.remove('/tmp/.usb0_indexed')
              except Exception:
                  pass
              # Index the box's own content again (check_internal_content)
              try:
                  os.remove(INTERNAL_INDEXED)
              except Exception:
                  pass
          whole_disk.discard(chr(mnt[j]))
          loc[j]= -1
          mnt[j] = -1
          j += 1
        elif mounted_device('/media/usb' + chr(loc[j])) != '/dev/' + usb_device_name(chr(mnt[j])):
          # The key is still plugged in but no longer mounted where we put it:
          # another program moved or unmounted it (the front panel's copy
          # commands move it to /media/usb11).  Forget this slot, or the key
          # is mounted again at the NEXT free slot (/media/usb1) while usb0
          # stays booked for it.  A key that was at usb0 is mounted there again
          # below and indexed again (sentinel removed).
          logger.info("/dev/" + usb_device_name(chr(mnt[j])) + " is no longer mounted at /media/usb" + chr(loc[j]) +
                      ": forgetting that mount, time is " + time.asctime())
          if loc[j] == ord('0'):
              try:
                  os.remove('/tmp/.usb0_indexed')
              except Exception:
                  pass
          loc[j] = -1
          mnt[j] = -1
          j += 1
        else:
        #Were here with the device still mounted
          print("device still mounted /dev/"+usb_device_name(chr(mnt[j]))+" Device present")
          # First poll after usb0 is mounted (or after boot, since the sentinel
          # lives in /tmp): index the USB once.  The sentinel stops it re-running
          # every poll; it is removed when the USB is unplugged.
          if loc[j] == ord('0') and not os.path.isfile('/tmp/.usb0_indexed'):
            logger.info("Start load content for menu's, time is " + time.asctime())
            try:
                os.system("rm /usr/local/connectbox/complex_dir 2>/dev/null")
            except:
                pass
            start_content_loader()
            try:
                open('/tmp/.usb0_indexed', 'w').close()
            except Exception:
                pass
          j += 1
          total += 1
      else:
        #were here because there was no mount device detected
        if DEBUG > 2: print("device not mounted usb", j)
        j += 1



    # SSH Enabler: run after every removal-pass iteration.
    # Checks for /media/usb0/.connectbox/enable-ssh and starts sshd if found.
    # Running this unconditionally (not just on insertion) ensures a key inserted
    # while the daemon is already running can still trigger SSH activation.
    os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active --quiet ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")



    # --- Pass 2: Detect new USB insertions and mount them ---
    # Re-parse the same lsblk snapshot line by line.  For each line that contains
    # an sdX1 pattern, determine whether it is already mounted (lsblk shows "usb"
    # or "part /" in the same line).  If not mounted:
    #   - Find the lowest free /media/usbN slot by scanning loc[] for -1 entries
    #     and f[] (a bitmap of used usb numbers) for gaps.
    #   - Create the /media/usbN directory if it does not exist.
    #   - Run dosfsck (FAT) or ntfsfix (NTFS) for filesystem integrity before
    #     mounting -- a corrupted FAT table can cause mount to hang the process.
    #   - Attempt a FAT mount first (covers FAT16/32/exFAT); if that returns
    #     non-zero, retry with explicit -t ntfs.
    #   - Kernel >= 5.15 uses the unified "utf8" mount option; older kernels need
    #     "iocharset=utf8".  The kernel version is read once via "uname -r".
    #   - Record the successful mount in mnt[j] and loc[j], increment total.
    #   - If the newly mounted drive is usb0, trigger SSH-enabler, upgrade script,
    #     and the upgrade script.
    # If already mounted, register it in the mnt[]/loc[] table if not already there
    # (handles the case where the drive was mounted before this daemon started).
    i=0                       #line iterator
    j=0                       #used for finding sdx1's
    k=0                       #used for usb mount
    c = b.partition("\n")
    listing = b               # b is reused below for mount commands; keep the lsblk text
# while we have lines to parse we check each line for an sdx1 device and mount it if not already
    while ((c[0] != "") and (i<35)):
      if DEBUG > 2: print("Loop 2, iterate:",i, c[0])
      d[i] = c[0]
      e = match_usb_device(d[i], listing)                 # sdX1, or a whole-disk sdX with a file system
      if e and not (('usb' in d[i]) or ('part /' in d[i])) and (e.group() in failed_mounts):
        if DEBUG > 2: print("/dev/"+e.group()+" failed to mount earlier; not retrying until it is re-inserted")
      elif e:
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
# we have a problem our mount point is to high.  we need to do a reboot.
          if k > 9:
            logger.info("We have a problem mount point is too high, we will reboot!, time is " + time.asctime())
            os.sync()
            os.system("/usr/sbin/reboot")
#          time.sleep(20)    #This ends here.
# Now we know we need to do a mount and have found the lowest mount point to use in (a)
          clear_dead_mounts("/media/usb"+chr(a))
          if not (os.path.exists("/media/usb"+chr(a))):  #if the /mount/usbx isn't there create it
            res = os.system("mkdir /media/usb"+chr(a))
            if DEBUG > 2: print("created new direcotry %s","/media/usb"+chr(a))
          x = Popen(["uname", "-r"], stdout=PIPE)
          y = str(x.communicate()[0])
          x.stdout.close()
          # Linux file systems (ext4 etc.) are mounted by their own type and
          # without the utf8 option, which only FAT-family drivers accept.
          fstype = get_fstype(e.group())
          if fstype in POSIX_FILESYSTEMS:
            b = "mount /dev/" + e.group() + " -t " + fstype + " -o noatime,nodev,nosuid" + " /media/usb" + chr(a)
          elif y>="5.15.0":
            b = "mount /dev/" + e.group() + " -t auto -o noatime,nodev,nosuid,utf8" + " /media/usb" + chr(a)
          else:
            b = "mount /dev/" + e.group() + " -t auto -o noatime,nodev,nosuid,iocharset=utf8" + " /media/usb" + chr(a)
          # dosfsck/ntfsfix only understand FAT/NTFS; Linux file systems are
          # mounted as-is (the kernel replays the ext4/xfs journal on mount).
          if fstype in POSIX_FILESYSTEMS:
            print("/dev/" + e.group() + " is " + fstype + ": skipping dosfsck/ntfsfix")
            logger.info("/dev/" + e.group() + " is " + fstype + ", no FAT/NTFS check needed, time is " + time.asctime())
          else:
            # The check is chosen by file system type (as the front panel's
            # usb.py does).  It used to run dosfsck -a on every non-Linux key
            # and ntfsfix when dosfsck exited 1 - which also means "errors
            # corrected" on FAT - and it waited with no limit: a clean 64 GB
            # FAT32 card kept PxUSBm busy for over 7 minutes (2026-10-29).
            dev = e.group()
            cmd = None
            if fstype == 'vfat':
              if fat_needs_check(dev):
                cmd = ['dosfsck', '-a', '/dev/' + dev]   # exit 0 = clean, 1 = errors corrected
              else:
                logger.info("/dev/" + dev + " FAT marked clean: no dosfsck needed, time is " + time.asctime())
            elif fstype == 'ntfs':
              cmd = ['ntfsfix', '-d', '/dev/' + dev]     # clears the dirty flag ntfs-3g refuses
            else:
              logger.info("/dev/" + dev + " is " + (fstype or "of unknown type") + ": no check before mount, time is " + time.asctime())
            if cmd:
              starttime = time.time()
              logger.info("Checking the file system before mount: " + " ".join(cmd) + ", time is " + time.asctime())
              res = run_fs_check(cmd)
              logger.info("Completed " + " ".join(cmd) + " result " + str(res) + " in " + str(int(time.time() - starttime)) + " seconds")

###################### OK now mount the key ############################################
          print("trying to do mount: " + b)
          try: # general fat mount
            res = os.system(b)				#do the mount
            print("Result of mount was: "+str(res))
            logger.info("Completed mount " + b + " result " + str(res) + " time is " + time.asctime())
          except:
            print("mount" + b + " failed result was: "+str(res))
            logger.info("mount" + b + " failed result was: "+str(res) + " time is " + time.asctime())
          # After a good mount the "Checking USB" message stays until it goes
          # stale (15 s) and indexing takes the panel over; after a failed one
          # the panel goes back to normal at once.
          if res != 0:
            show_usb_check(False)
          if res != 0:
####################### we didn't mount fat drive try NTFS drive #######################
            try:   #try explicit ntfs mount
              # (No "sync" option: on ntfs-3g it slowed writes to about
              # 0.1 MB/s on .200, against about 9 MB/s without it.)
              if (res > 0):		#if we have res > 0 then we have an error
                 if y>= "5.15.0":
                    b = "mount /dev/" + e.group() + " -t ntfs -o noatime,nodev,nosuid,utf8" + " /media/usb" + chr(a)
                 else:
                    b = "mount /dev/" + e.group() + " -t ntfs -o noatime,nodev,nosuid,iocharset=utf8" + " /media/usb" + chr(a)
                 res = os.system(b)
                 print("tried new NTFS mount of: "+b + "result was: " + str(res))
                 logger.info("Retried NTFS mount of "+b+" with result of "+str(res) + " time is " + time.asctime())
            except:
              logger.info("on NTFS  mount of USB key errored")
              print("on NTFS mount of USB key errored,  res =" + str(res))
              res = -1
          if DEBUG > 2: print("completed mount /dev/",e.group)
          # os.system returns 0 only on success.  (This used to test res >= 0,
          # which is always true, so a failed mount was recorded as mounted and
          # an empty /media/usb0 got indexed.)
          if res != 0:
            failed_mounts.add(e.group())
            logger.info("Could not mount /dev/" + e.group() + " (" + (fstype or "unknown") + "), will retry when re-inserted, time is " + time.asctime())
          else:
            mnt[j]=ord(e.group()[2])                        # drive letter: 'sdb1' or 'sdb' -> 'b'
            if e.group() == 'sd' + e.group()[2]:
              whole_disk.add(e.group()[2])
            loc[j]=a
            total += 1
            print("value of a is: "+chr(a))
            logger.info("Ok we completed the mount on  /dev/sda"+chr(a))

            if a == ord('0'):
              print("Ok we have a mount on usb0 so we need to check for ccontent") 
          # Run these functions on mount -- added 20211111
              # SSH Enabler
              os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active --quiet ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")
              # Enhanced Content Load
              print("Start load content for menu's")
              logger.info("Starting content indexing and load on  /dev/sda1, time is " + time.asctime())
              logger.info("Finished content indexing and load on /dev/sda1, time is " + time.asctime())

              # upgrade enabler
              if (os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/upgrade/upgrade.py'")) == 0:
                print("starting the upgrade process\n")
                logger.info("starting the upgrade process due to /media/usb0/.connectbox/upgrade/upgrade.py, time is "+ time.asctime())
                os.system("python3 /media/usb0/.connectbox/upgrade/upgrade.py")
                logger.info("Ended upgrade, time is " + time.asctime())
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
# We know if we found usb? in the table if k < 10
                if k == 10 and j < 10:                          #mount was not in table to so add it
                  loc[j] = l                                    #set loc to usb(l) at j sice we didn't find it
                  mnt[j] = ord(e.group()[2])                    #set mnt to the drive letter to finish the mount registration
                  if e.group() == 'sd' + e.group()[2]:
                    whole_disk.add(e.group()[2])
                  if DEBUG > 2: print("/dev/"+e.group()+" is already mounted as usb"+chr(l)+"but we added it to the table")
                  if l == 0:
                      logger.info("We already had a USB that was mounted but added it to our mount table so starting loading cocntent, time is "+ time.asctime())
                      print("Start load content for menu's")
                      # SSH Enabler
                      os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active --quiet ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")
                else:
                  if DEBUG > 2: print("/dev/"+e.group()+" was mounted and in the table at ",k)
              else:
                if DEBUG > 2: print("USB number >= 10 ", a[2], " We will unmount it")
                b = 'umount /media/usb'+a[2]
                res = os.system(b)
            else:
              if DEBUG > 2: print("Error parsing usb# in line", i)
          else:
              if DEBUG > 2: print("/dev/sdx1 is already mounted but not as usb", d[i])
      c = c[2].partition("\n")
      i += 1

    # --- Pass 3: Compact the mount table ---
    # After insertions and removals, mnt[] and loc[] may have holes (slots set back
    # to -1 while later slots still hold valid entries).  The rest of the code and
    # the main loop assume the arrays are densely packed from index 0, with `total`
    # being an accurate count of active mounts.  This pass uses a two-pointer bubble
    # to move every occupied slot left to fill any gaps, then sets total = j+1.
    # Why compact rather than just scan for -1 gaps each time?  Because Pass 2 uses
    # the first -1 slot in loc[] to decide where to register a new mount.  Holes
    # left by removals would be found before higher-numbered occupied slots,
    # potentially causing the next insertion to reuse a slot that lsblk still shows
    # as mounted (race condition on rapid insert/remove cycles).
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

# remove any holes in mount table
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



def end_client_dhcp_wait():
    """
    Stop dhclient on the Wi-Fi interfaces before an expansion reboot.

    The expansion reboots come about 25 s after start-up.  By then ifup for the
    client Wi-Fi interface is usually still in dhclient, asking for an address
    on a network that is not set up; it gives up only after dhclient's 60 s
    timeout and holds the interface's lock (/run/network/ifstate.wlanN) until
    then.  The shutdown's ifdown waits for that lock, so the reboot hung for up
    to a minute on "A stop job is running for ifup for wlan0" (2026-10-29).
    Ending dhclient lets ifup finish and release the lock.  The access point
    interface has no dhclient, and eth0 is left alone (its address is released
    at shutdown as usual).
    """
    try:
        r = subprocess.run(["pkill", "-f", r"dhclient.* wlan[0-9]+( |$)"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            logger.info("Stopped the client Wi-Fi DHCP wait before the expansion reboot")
            time.sleep(1)
    except Exception as e:
        logger.info("Could not stop dhclient before the reboot: " + str(e))


def do_resize2fs(rpi_platform, rm3_platform):
    """
    Expand the root filesystem to fill the full partition that was enlarged by do_fdisk().

    This is the second phase of the two-phase partition-expansion sequence.  It is
    called only when expand_progress.txt contains "fdisk_done", meaning fdisk has
    already moved the partition boundary to the end of the storage device.
    resize2fs then tells the ext4 filesystem to grow into that space.

    Platform selection logic:
        - RM3 (Radxa CM3): uses /dev/mmcblk1p<max_partition>
        - Raspberry Pi / CM4 with connectbox_scroll (multi-partition layout):
              uses /dev/mmcblk0p<max_partition>
        - Raspberry Pi / CM4 single-partition: uses /dev/mmcblk0p2
        - NEO / other: uses /dev/mmcblk0p1

    On success, writes "resize2fs_done" to expand_progress.txt, syncs, and reboots.
    If resize2fs output does not contain "blocks long" (i.e. the filesystem was already
    the right size or the resize failed silently) the function returns without rebooting
    and without updating the progress file -- the caller should handle this case.

    Parameters:
        rpi_platform (bool): True when running on a Raspberry Pi or CM4 board.
        rm3_platform (bool): True when running on a Radxa CM3 (Rock) board.

    Returns:
        None  (either reboots the system on success, or returns silently on failure)
    """
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
        logger.info("doing a reboot after the resize")
        end_client_dhcp_wait()
        os.system('shutdown -r now')


def do_fdisk(rpi_platform, rm3_platform):
    """
    Use fdisk (via pexpect) to delete and recreate the root partition so it occupies
    the full available space on the storage device.

    This is the first phase of the two-phase partition-expansion sequence.  The
    original image ships with a small partition (2-3 GB).  On first boot, this
    function interactively drives fdisk to:
        1. Print partition info and extract the starting sector of the last partition.
        2. Delete the last partition.
        3. Create a new primary partition starting at the same sector but extending
           to the end of the device (default last sector).
        4. Decline to remove the existing filesystem signature ("N") so that
           resize2fs can expand into the new space on the next boot.
        5. Write the changes and reboot.

    The starting sector is preserved exactly so that the existing ext4 superblock and
    data remain intact -- only the partition table entry changes.  resize2fs (called
    on the following boot via do_resize2fs) then makes the filesystem aware of the
    larger boundary.

    Platform differences:
        - RM3 uses /dev/mmcblk1; all others use /dev/mmcblk0.
        - RPi/CM4 has a two-partition layout; NEO has a single-partition layout.
          The partition-number prompts from fdisk differ between these, so the
          interactive sequence branches accordingly.
        - connectbox_scroll is set True when fdisk output reveals a /dev/mmcblk0p5
          partition (the Connectbox Scroll hardware variant).

    After writing changes, "fdisk_done maxp=<N>" is written to expand_progress.txt
    (where N is the last partition number), then the system reboots.

    Parameters:
        rpi_platform (bool): True when running on a Raspberry Pi or CM4 board.
        rm3_platform (bool): True when running on a Radxa CM3 (Rock) board.

    Returns:
        None  (always reboots before returning)
    """
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

  # --- Parse the existing partition layout ---
  # Send "p" to print the partition table.  pexpect captures everything fdisk
  # outputs before returning to the "Command (m for help):" prompt, which is
  # stored in child.before as bytes.  We decode to UTF-8 and use regex to find
  # the last partition's line (e.g. "/dev/mmcblk0p2   532480   ...") and extract
  # the starting sector number from it.  The starting sector is the critical value
  # we must preserve -- it marks where the filesystem data begins.
  # Detecting "/dev/mmcblk0p5" identifies Connectbox Scroll hardware which has a
  # five-partition layout (boot + root + three data partitions).
  # "p" get partition info and search out the starting sector of mmcblk0p1
    child.sendline('p')
    i = child.expect('Command (m for help)*')
  # the child.before contains all that came BEFORE we found the expected text
  #logger.info (child.before)
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
    logger.info("delet partition")

    if rpi_platform or rm3_platform:    # CM4 & RM3 has 2 partitions... select partition 2
        i = child.expect('Partition number')
        child.sendline(str(x))
        logger.info("send partiton"+str(x))
    i = child.expect('Command (m for help)*')
    logger.info("found Command (m for help)*")
# print("after delete ",child.before)

  # "n" for new partition
    child.sendline('n')
    logger.info("Sent n for new partition")
    if rm3_platform:
      logger.info("looking for default 2 since were rm3_platform")
      i = child.expect('default 2')
      child.sendline(str(x))
      logger.info("sent partition number")
      i = child.expect('First sector')
      logger.info("Got First Sector question back")
    else:
      i = child.expect('(default p):*')
      logger.info("got back (default p):* question")
      # "p" for primary partition
      child.sendline('p')
      logger.info("Sent the p commannd")
      if rpi_platform:    # CM4 has 2 partitions... select partition 2
        logger.info("expecting 'default 2*' from RPI_Platform")
        i = child.expect('default 2*')
        logger.info("got the result and sending the stating sector")
        child.sendline(str(x))                 # "2" for partition number 2
        i = child.expect('default 2048*')
        logger.info("Ok expected default 2048* and got it")
# print("after new ",child.before)
      else:
          logger.info("not rpi_Platform so expecting default 1*")
          i = child.expect('default 1*')      # "1" for partition number 1
          logger.info("ok got it")
          child.sendline('1')
          logger.info("sent 1st partition")
          i = child.expect('default 2048*')
          logger.info("got default 2048* for starting sector")
# logger.info (child.before)

  # send the startSector number
    child.sendline(startSector)
    logger.info("sent starting sector")
    logger.info("after new starting sector came: %s", child.before)
    logger.info("then: %s", child.after)
#    i = child.expect('Last*')
    logger.info("expected Last* and got it")
# print("At last sector... the after is: ", child.after)

  # take default for last sector
    child.sendline('\n')
    logger.info("sent balnk line to take default ending sector")
    i = child.expect('signature*')

  # "N" don't remove the signature
    child.sendline('N')
    i = child.expect('Command (m for help)*')

  # "w" for write and exit
    child.sendline('w')
    i = child.expect('Syncing disks*')

    logger.info("exiting the fdisk program... now reboot")
    f = open(progress_file, "w")
    f.write("fdisk_done   maxp="+str(max_partition))
    f.close()
    os.sync()
    # Disk is now the right size but the OS hasn't necessarily used it.
    logger.info( "PxUSBm is rebooting after fdisk changed")
    os.sync()
    end_client_dhcp_wait()
    os.system('shutdown -r now')
    return()


# called by main()

def check_iwconfig(b):
  """
  Check whether the specified wireless interface is operating in Access Point
  (Master) mode, indicating the AP is up and broadcasting.

  Runs ``iwconfig`` and searches the output for the interface name followed by
  "Mode:Master".  This is used by the main loop to detect a dropped AP and trigger
  a recovery (ifdown/ifup, hostapd restart, or full getNetworkClass() call).

  Parameters:
      b (int): The wlan interface number to check (e.g. 0 for wlan0, 1 for wlan1).

  Returns:
      int: 1 if wlan<b> is present in iwconfig output and shows "Mode:Master",
           0 otherwise (interface absent, not in Master mode, or iwconfig failed).
  """
# run iwconfig parameter and check for "Mode:Master"
# if found return 1 to indicate the wlan associated with the AP is up
#  else, return a 0

  wlanx = "wlan"+str(b)
# check to see if that did it...
  cmd = "iwconfig"
  # stderr discarded: iwconfig complains "no wireless extensions" about lo and
  # eth0 on every call, which only filled the journal.
  rv = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
  rvs = rv.decode("utf-8").split(wlanx)

  if (len(rvs) >= 2):       # rvs is an array split on wlanx
    wlanx_flags = str(rvs[1]).find("Mode:Master")
    if (wlanx_flags) >= 0:
      # Master mode alone is not enough: after a USB re-plug of the AP adapter
      #  the interface stayed in Master mode with its link down and nothing on
      #  the air, while hostapd kept saying ENABLED or had given up (CM4 on
      #  Trixie, 2026-11-04).  So also check the link and hostapd.
      return(1 if ap_really_up(wlanx) else 0)
    else:
      return 0
  return(0)


def ap_really_up(wlanx):
  """
  Extra AP checks for check_iwconfig(): the AP link must not be down, and
  hostapd must be running ENABLED on this interface.

  Only clear failures count, so a working AP is never restarted by mistake:
  an operstate other than "down" (e.g. "unknown" from older drivers) is
  accepted, and the hostapd check is skipped when hostapd_cli is not installed.
  (iw's ssid line is not used: the 8812au driver does not always report it
  while beaconing.)

  Returns True when no failure was found.
  """
  try:
    with open("/sys/class/net/"+wlanx+"/operstate") as f:
      if f.read().strip() == "down":
        logger.info("AP check: "+wlanx+" is in Master mode but its link is down")
        return False
  except OSError:
    return False
  if shutil.which("hostapd_cli"):
    try:
      out = subprocess.run(["hostapd_cli", "-i", wlanx, "status"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=10).stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
      return True             # hostapd busy: do not decide on that
    if "state=ENABLED" not in out:
      logger.info("AP check: hostapd is not ENABLED on "+wlanx+": "+out.strip().replace("\n", " ")[:120])
      return False
  # The radio itself (2026-11-05): after an 8812au driver reload hostapd said
  # ENABLED, but iw showed no channel and txpower -100 dBm and no beacon went
  # out until hostapd was restarted.  Only when iw answers at all.
  if shutil.which("iw"):
    try:
      info = subprocess.run(["iw", "dev", wlanx, "info"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=10).stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
      return True
    if "type AP" in info:
      m = re.search(r"txpower (-?[0-9.]+) dBm", info)
      if "channel " not in info or (m and float(m.group(1)) <= 0):
        logger.info("AP check: hostapd is ENABLED on "+wlanx+" but the radio has no channel or no transmit power: " +
                    " ".join(l.strip() for l in info.split("\n") if "channel" in l or "txpower" in l)[:120])
        return False
  return True


def restart_hostapd():
  """Restart hostapd, clearing a failed state first: after several quick
  failures systemd refuses starts for a while ("Start request repeated too
  quickly")."""
  os.system("/bin/systemctl reset-failed hostapd 2>/dev/null; /bin/systemctl restart hostapd")



def dbCheck():
       """
       Verify that the MySQL/MariaDB service is running and restart it if not.

       Called on every main-loop iteration when ``connectbox_scroll`` is True (i.e. on
       the Connectbox Scroll hardware variant which uses a database for content).
       A failed database causes the content-serving web application to return errors to
       clients, so this provides a lightweight self-healing mechanism without requiring
       a full system reboot.

       Logic:
           1. Query systemctl for the mysql service status.
           2. If "active (running) since" is found in the output, the DB is healthy --
              return 0 immediately.
           3. Otherwise, attempt a ``systemctl restart mysql`` and re-check.
           4. Return 0 if the restart succeeded, 1 if the database is still not running.

       Returns:
           int: 0 if MySQL is running (either initially or after a successful restart),
                1 if MySQL could not be started.
       """
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
  """
  Detect the ConnectBox hardware platform by reading /proc/cpuinfo.

  Reads the "Revision" field from /proc/cpuinfo and maps the hex revision code to a
  human-readable version string (e.g. "PI 4B 4GB 1.4").  Special cases:
      - "Radxa CM3 IO" in any cpuinfo line -> returns "Rock CM3"
      - revision "0000" -> NanoPi NEO
      - revision "4"    -> Orange Pi Zero 2
      - revision "RM3"  -> Rock CM3

  If /proc/cpuinfo cannot be parsed (empty revision, unknown board, or exception),
  the function falls back to ``lshw -short`` and looks for a "system" entry.
  Orange Pi Zero 2 variants are normalised to "OrangePiZero2".

  The returned string is used at startup to set ``rpi_platform``, ``rm3_platform``,
  ``PI_stat``, and ``OP_stat`` flags, which control partition layout, network
  interface naming, and OLED display behaviour throughout the daemon.

  Returns:
      str: A short hardware description string such as "PI 4B 4GB 1.4",
           "OrangePiZero2", "Rock CM3", "NEO NANOPI", "Unknown", or "Error".
  """
  global DEBUG

  if DEBUG > 3: print("Started Revision test")
  revision = ""
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if 'Radxa CM3 IO' in line: revision = "RM3"
      elif "Revision" in line:
        logger.info("revision of hardware is: "+line)
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
      # CM4 (with or without eMMC: the Lite has the same codes).  The third hex
      #  digit is the memory size: a=1GB b=2GB c=4GB d=8GB (a 4GB CM4 Lite
      #  reports c03140, 2026-11-04).
      elif revision== "a03140": version="CM4 1GB 1.0"
      elif revision== "b03140": version="CM4 2GB 1.0"
      elif revision== "c03140": version="CM4 4GB 1.0"
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
          logger.info("revision of hardware is : "+l)
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
    """
    Ensure all network interfaces use standard kernel names (ethX, wlanX).

    Newer Linux kernels assign predictable-but-non-standard names to network
    interfaces (e.g. "enp3s0", "wlxaabbccddee").  ConnectBox configuration files
    (hostapd.conf, dnsmasq.conf, /etc/network/interfaces) all rely on "wlan0",
    "wlan1", "eth0" etc.  This function detects non-standard names and creates
    systemd .link files under /etc/systemd/network/ that bind each interface's
    MAC address to a standard name, then reboots so the names take effect.

    Algorithm:
        1. Run ``lshw -c Network`` and split on "*-network:" to get one block per
           interface.
        2. For each block, extract the "logical name" and "serial" (MAC address).
        3. If the logical name already matches ethX or wlanX format, record it in
           ``ethntwk`` or ``wlanntwk`` and move on -- no link file needed.
        4. If the name is non-standard, find the lowest unused ethN or wlanN number
           (not already claimed by a standard-named port or an existing .link file),
           write a systemd .link file that maps the MAC to that standard name, and
           set a flag (z=1) indicating a reboot is required.
        5. If any .link files were written, sync and reboot. The reboot causes
           systemd-udevd to apply the new names before any service starts.

    Why .link files instead of udev rules:
        systemd-networkd .link files are the modern, distribution-agnostic mechanism
        for persistent interface renaming.  They are evaluated early in boot before
        network services start, ensuring all downstream configuration sees the correct
        interface names.

    Returns:
        None  (may reboot the system if link files were written)
    """
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

    logger.info("got to set network names")
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
                logger.info("Found network name of device: "+ntwk)
                if len(ntwk) > 3:
                    if ((ntwk[-1].isnumeric()) and  (ntwk[0:-2] in "wlan eth")):
                        logger.info("Found port "+ntwk+" that is within our standard.")
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
                        logger.info("Identifier for this network port is: "+idnt)
                        if ((len(idnt) > 0) and (len(idnt) < 18)):
                            #OK the name is not in the standard format and we will have to add a link file for this one.
                            #But we will first add it to the list that needs to be done.
                            netwk.append(tuple([ntwk,idnt]))
                            x += 1
                        else:
                            #didn't have a coorrectly formated identifier in the way of a mac address
                            logger.info("Couldn't get a mac address for port "+ntwk+" so having to skip it!")
                            x += 1
                    else:
                        #There was not a serial in the network list making it impossible to get the mac address
                        logger.info("Couldn't get a mac address for port "+ntwk+" so having to skip it!")
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
                    logger.info("Couldn't write the ethernet port link file for eth"+str(y))
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
                    logger.info("Couldn't write the wifi port link file for wlan"+str(y))
                    print("Couldn't write the wifi port file")
                    f.close()
                #this is an entry we don't recognize so we ignore it
                logger.info("Ignoring interface: "+netwk[x][0]+" with Mac address of : "+netwk[x][1])
                print("Ignorioing interface: "+netwk[x][0]+" with mac address of : "+netwk[x][1])

            x += 1				#Increment to the next entry if there is one


        if z != 0:				# Now that were done check to see if we need to call a reboot
            os.sync()
            print("We wrote new files so we reboot")
            os.system("sudo reboot")		#NOTE we will not return from here.   We will just restart.
    return




# getNetworkClass() ported from connectbox-hat-service / cli.py

def getNetworkClass(level):
    """
    Identify which wireless interface serves as the Access Point (AP) and which
    serves as the Client Interface (CI), then apply any necessary configuration
    changes.

    ConnectBox uses two wireless interfaces when a USB WiFi dongle (RTL8812AU/BU or
    RTL88192U) is present: the RTL dongle becomes the AP because it supports the
    required AP mode and higher throughput, while the on-board BCM WiFi (brcmfmac)
    becomes the client-facing uplink.  Without a dongle, the single on-board chip
    acts as the AP.

    Detection logic (in priority order):
        - If wlan0 driver contains "rtl88" -> AP=wlan0, CI=wlan1
        - If wlan1 driver contains "rtl88" -> AP=wlan1, CI=wlan0
        - If wlan0 driver is "brcmfmac"    -> AP=wlan1, CI=wlan0
        - Fallback                         -> AP=wlan0, CI=wlan1
        - Only one wlan found              -> AP=that wlan, CI="" (no uplink)

    After identifying AP and CI, calls ``fixfiles(AP, CI)`` to update
    /etc/network/interfaces, /etc/dnsmasq.conf, /etc/hostapd/hostapd.conf, and
    /etc/dhcpcd.conf if they do not already reflect the current assignment.
    If files were changed, brings interfaces down and up to apply the new config.

    The ``level`` parameter is reserved for future use to control the aggressiveness
    of the interface-restart sequence (level=1 is the minimal/fastest restart).

    Parameters:
        level (int): Severity level of the fix attempt. 1 = least severe (minimal
                     ifconfig down/up). Higher values trigger more aggressive resets.

    Returns:
        int: Value returned by fixfiles() -- 1 if config files were changed and
             services were restarted, 0 if no changes were needed, or 0 if the
             interface topology could not be determined (no wlan found, or >2 wlans).
    """
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
#    logger.debug("starting the get network class tool of cli.py on the battery page")
    res = os.popen("lshw -c Network").read()
    i=3
    if "wlan" in res:
        r = res.split("wlan")
        while i > 1:
            if len(r) <= 1:
                a = ""
            else:
                a = r[1][0]
            if a != "":
                if r[1].find("driver="):
                    b = r[1].split("driver=")[1].split(" ")[0]             #Split out the driver from the configuration line
                    netwk.append([a,b])                                    #add the wlan# and driver to the list
                    logger.info("found wlan driver combo, wlan"+a+" driver: "+b)
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
    logger.info("We finished the wlan lookup and are now going to edit the files.")
    AP = ""                                                         #access point interface
    CI = ""                                                         #client interface
    if len(netwk) == 1:                                             #only one wlan interface AP only
        a = netwk[0][0]
        b = netwk[0][1]
        logger.info("single interface wlan"+a+" with driver "+b)
        # now we need to update the files for a single AP and no client
        AP = a;

    elif len(netwk) > 1:                                            #multiple wlan's so both AP and client interfaces
        logger.info("wlan"+netwk[0][0]+" with driver "+netwk[0][1])
        logger.info("wlan"+netwk[1][0]+" with driver "+netwk[1][1])
            # we have an rtl driver on this first wlan
        # Realtek USB adapters: out-of-tree drivers are rtl88xx..., the kernel's
        #  own are rtw88_... (e.g. rtw88_8812au on Raspberry Pi OS Trixie)
        if "rtl88" in netwk[0][1] or "rtw88" in netwk[0][1]:      #if we have an rtl on the first wlan we will use it for AP
            AP = netwk[0][0]
            CI = netwk[1][0]
            #regardless of what we have there since its RTL-X we will use it for AP since we have no others
        elif "rtl88" in netwk[1][1] or "rtw88" in netwk[1][1]:      #if we have an rtl on the second wlan we will use it for AP
            AP = netwk[1][0]                                    #interface 2 has the rtl and will be AP
            CI = netwk[0][0]                                    #interface 1 is on board or other andd will be the client side for network
        elif "brcmfmac" in netwk[0][1]:
            AP = netwk[1][0]
            CI = netwk[0][0]
        else:
            AP = netwk[0][0]
            CI = netwk[1][0]



        logger.info("AP will be: wlan"+AP+" ethernet facing is: wlan"+CI)
        if len(netwk) >=3:
            logger.info("we have more interfaces so they must be manually managed") # if we have more than 2 interfaces then they must be manually managed. 
# --- no files changed (more than 2 interfaces... how to handle??) ---
            return(0)

    else:                                                           # we don't have even 1 interface
        logger.info("We have no wlan interfaces we can't function this way, rebooting to try to find the device")
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

def network_files_match(a):
  """
  True if the files fixfiles() writes all serve the AP on wlan<a>: the static
  AP stanza in /etc/network/interfaces, dnsmasq's interface= and hostapd's
  interface=.  wificonf.txt alone is not proof (2026-11-05: it named wlan1
  while interfaces and dnsmasq.conf, never put in place, still named wlan0).
  A file that cannot be read counts as not matching.
  """
  try:
    with open("/etc/network/interfaces", encoding="utf-8") as f:
      if not re.search(r"^iface wlan" + a + r" inet static", f.read(), re.M):
        return False
    with open("/etc/dnsmasq.conf", encoding="utf-8") as f:
      if not re.search(r"^interface=wlan" + a + r"\s*$", f.read(), re.M):
        return False
    with open("/etc/hostapd/hostapd.conf", encoding="utf-8") as f:
      if not re.search(r"^interface=wlan" + a + r"\s*$", f.read(), re.M):
        return False
  except OSError:
    return False
  return True


def fixfiles(a, c):
    """
    Rewrite network configuration files to bind the correct wlan interface numbers
    to the AP and Client Interface roles, then restart the affected services.

    This function is the workhorse called by getNetworkClass() when the detected
    AP/CI assignment differs from what is recorded in wificonf.txt, or when the
    hostapd.conf SSID does not match the current Brand name.

    Files updated (via .tmp intermediates, then mv into place):
        /etc/network/interfaces  -- wlan numbers substituted for AP and CI sections
        /etc/dnsmasq.conf        -- interface= line updated to AP wlan
        /etc/hostapd/hostapd.conf -- interface= and ssid= lines updated
        /etc/dhcpcd.conf         -- denyinterfaces updated to CI wlan (or removed if
                                    no CI), interface= line updated to AP wlan
        /usr/local/connectbox/wificonf.txt -- written last as the canonical record;
                                    if this file agrees with lshw output on the next
                                    boot the entire rewrite is skipped (fast path).

    The .j2 template for /etc/network/interfaces uses a #CLIENTIF# marker to
    separate AP directives from CI directives.  Lines containing "wlan" have their
    numeric suffix replaced with the correct interface number.  If CI is absent
    (c == ""), the CI section is commented out entirely.

    Why write .tmp then mv:
        Writing to a temp file and then moving (cp) avoids leaving a partially-written
        config file on disk if the process is interrupted, which would prevent the
        network from coming up on the next boot.

    Parameters:
        a (str): The wlan number (as a string, e.g. "0") that will serve as the
                 Access Point interface.
        c (str): The wlan number (as a string) that will serve as the Client
                 Interface uplink, or "" if there is no CI (single-wlan devices).

    Returns:
        int: 1 if config files were changed and network services were restarted,
             0 if the existing config already matched and no changes were needed.
    """
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

    logger.debug("Entering fix files")
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
    logger.info("wificonf.txt holds "+ct[0]+" and "+ct[1]+" for detected paramaters (AP, Client) "+a+" and "+c)

    if ("AccessPointIF=wlan"+ a) == ct[0] and (("ClientIF=wlan"+ c == ct[1] and c!="") | (c == "" and ct[1] == "ClientIF=")):
        f = open("/etc/hostapd/hostapd.conf","r")
        g = f.read()
        f.close()
        if (Brand['Brand'] in g) and network_files_match(a):
	        logger.info("Skipped file reconfiguration as the configuration is the same")
	        print("nothing to do")
#        os.system("ifup wlan"+a)   # restart wlan ... other restarts needed??n

# if wificonfig.txt agrees with info from lshw we can continue without changing anything
        	return(0)

# if NOT, we cook the files and will restart the services with
    # Stop all network services before rewriting config files.  Writing to live
    # config files while hostapd/dnsmasq are running can cause them to re-read
    # partial data and enter an inconsistent state.  Stopping first is safe because
    # the interfaces will be brought back up after the files are in place.
    res = os.system("/bin/systemctl stop networking.service")
    res = os.system("/bin/systemctl stop hostapd")
    res = os.system("/bin/systemctl stop dnsmasq")
    res = os.system("/bin/systemctl stop dhcpcd")

# we only come here if we need to adjust the network settings
# Lets start with the /etc/network/interface folder
    # --- Rewrite /etc/network/interfaces from the .j2 template ---
    # interfaces.j2 is a template where wlan interface numbers are placeholders.
    # This loop reads the template line by line and substitutes the correct wlan
    # numbers for AP and CI sections.  The #CLIENTIF# marker line divides the file:
    #   - Lines before #CLIENTIF#: AP section; all "wlan" occurrences get the AP number.
    #   - Lines after #CLIENTIF#:  CI section; all "wlan" occurrences get the CI number.
    # If c=="" (no Client Interface), the CI section lines are commented out with "#"
    # and skip_rest=1 causes all remaining lines to be skipped once a non-wlan line
    # is seen (avoiding partial CI stanzas in the output).
    # The old numeric suffix after "wlan" is stripped digit by digit before the new
    # number is appended, so "wlan0" and "wlan1" in the template both become the
    # correct target interface regardless of what number the template used.
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
#                    logger.debug("on interface line were setting $1: "+n)
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
    logger.debug("we have finished the temp /etc/network/interfaces.tmp file")
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
#             logger.debug("on dnsmasq were setting $1: "+n)
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
    logger.debug("We have finished the temp /etc/dnsmasq.tmp file")
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
#             logger.debug("on hostapd were setting $1: "+n)
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
    logger.debug("We have finished the temp /etc/hostapd/hostapd.tmp file")

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
#             logger.debug("on dhcpcd.conf were setting $1: "+n)
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
    logger.debug("We have finished the temp /etc/dhcpcd.tmp file")

    os.system("sync")           #we will ensure we clear all files and pending write data

# Now we are done with the network/interface.tmp, dnsmasq.tmp and hostapd.tmp file creations time to put them into action.
    # ifdown is limited to 60 s (2026-11-05): a hung `iw scan` in the AP's
    #  ifup pre-up (wifi_configurator) held ifupdown's lock, ifdown waited for
    #  it for good and the new files below were never put in place.

    if a != "":
         logger.info("taking interface down wlan"+a)
         os.system("timeout 60 ifdown wlan"+a)

    if c != "":
         logger.info("taking interface down wlan"+c)
         os.system("timeout 60 ifdown wlan"+c)
    time.sleep(10)

#    logger.info("We have taken the interfaces down now")
    os.system("mv /etc/network/interfaces /etc/network/interfaces.bak")
    os.system("mv /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.bak")
    os.system("mv /etc/dnsmasq.conf /etc/dnsmasq.bak")
    os.system("mv /etc/dhcpcd.conf /etc/dhcpcd.bak")

    os.system("cp /etc/hostapd/hostapd.tmp /etc/hostapd/hostapd.conf")
    os.system("cp /etc/dnsmasq.tmp /etc/dnsmasq.conf")
    os.system("cp /etc/network/interfaces.tmp /etc/network/interfaces")
    os.system("cp /etc/dhcpcd.tmp /etc/dhcpcd.conf")

#  Now lets make sure we write out the configuration for future
#  (wificonf.txt reflects contents of all files which might need changes).
#  Written only now, after the new files are in place (2026-11-05: it used to
#  be written before ifdown; when ifdown hung, wificonf.txt said wlan1 while
#  interfaces and dnsmasq.conf still served the AP on wlan0, and every later
#  start took the "nothing to do" path, so phones got no DHCP).
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
    os.system("sync")

    os.system("/bin/systemctl daemon-reload")             #we reload all the daemons since we changed the config.
    time.sleep(5)
    print("finished fix files and exiting with a 1")
    logger.info("We have completed the file copies and daemon-reload")
#    logger.info("we will reboot to setup the new interfaces")

    return (1)      # indicates files were changed


def get_AP():
    """
    Read the Access Point wlan interface number from wificonf.txt.

    wificonf.txt is written by fixfiles() and contains lines of the form:
        AccessPointIF=wlan0
        ClientIF=wlan1

    This function extracts the numeric suffix from the AccessPointIF line and
    returns it as an integer.  It is called by the main loop and by checkServices()
    to know which wlan interface to monitor and restart if the AP goes down.

    Returns:
        int: The wlan interface number used as the Access Point (e.g. 0 for wlan0).

    Raises:
        Any exception from open() or int() if wificonf.txt is missing or malformed
        will propagate to the caller.
    """
    f = open("/usr/local/connectbox/wificonf.txt", "r")
    wifi = f.read()
    f.close()
    apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
    AP = int(apwifi.split("wlan")[1])
    return(AP)

def get_CI():
    """
    Read the Client Interface wlan number from wificonf.txt.

    Parses the "ClientIF=" line from wificonf.txt (written by fixfiles()).  If there
    is no Client Interface configured (single-wlan devices or no uplink dongle), the
    line will be "ClientIF=" with no number, and this function returns an empty string
    rather than raising an exception.

    Returns:
        int | str: The wlan interface number used as the Client Interface (e.g. 1 for
                   wlan1), or "" if no Client Interface is configured.
    """
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
  """
  Determine whether a Client Interface uplink connection is actually configured
  in wpa_supplicant.conf.

  Even if a CI wlan interface exists, it is only useful if wpa_supplicant has an
  SSID and PSK configured for it to connect to.  This function inspects
  wpa_supplicant.conf: if the "ssid" field is present but the "psk" section shows
  "Network" (indicating a placeholder/empty network block) or the ssid area
  contains "Password" (another empty-config indicator), the CI is considered
  unconfigured and 0 is returned.

  Returns:
      int: 1 if the CI appears to have a real SSID/PSK configured (uplink likely
           usable), 0 if wpa_supplicant.conf has no real network credentials.
  """
  f = open("/etc/wpa_supplicant/wpa_supplicant.conf")
  connections = f.read()
  f.close()
  ci_active = connections.partition("ssid")
  x = ci_active[2].split("psk")
  if "Network" in x[1]:
    return (0)        # we have no connection
  elif 'Password' in x[0]:
    return (0)		#We have no SSID
  else:
    return(1)



eth0_restart = [0.0]          # time of check_eth0's last eth0 restart

def eth0_dhclient_running():
  """True if the dhclient that ifup started for eth0 is still running."""
  try:
      with open('/run/dhclient.eth0.pid') as f:
          pid = int(f.read().strip())
      with open('/proc/%d/cmdline' % pid, 'rb') as f:
          cmd = f.read().split(b'\0')
      return any(c.endswith(b'dhclient') for c in cmd) and b'eth0' in cmd
  except Exception:
      return False

def check_eth0():
  """
  Check whether eth0 is connected and has an IP address, and attempt recovery if not.

  Parses ``ifconfig`` output for the eth0 interface and inspects the flags field:
      - flags=4099 (UP, BROADCAST, MULTICAST but no LOWER_UP): cable unplugged --
        no action needed, return 0.
      - flags=4163 (UP, BROADCAST, RUNNING, MULTICAST): cable plugged in, but if
        there is no IPv4 address the interface failed to get a DHCP lease.  If
        no dhclient is running for eth0, restart eth0 (background, at most
        every 5 minutes).
      - Any other flags value: unexpected state, return 1 (error).

  This is called on every 10th main-loop iteration (x % 10 == 0) to catch eth0
  stalls that can occur when the cable is connected after boot or after a DHCP
  server restart.

  Returns:
      int: 0 if eth0 is absent, unplugged, or has a valid IP address,
           1 if eth0 is in an unexpected or unrecoverable state.
  """
  process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
  stdout, stderr = process.communicate()
  net_stats = str(stdout).split("eth0")   # look for eth0 in ifconfig output
  if (len(net_stats) == 1):               # eth0 not found...  so we dont' have an issue
      return(0)
  # The flags number, e.g. "flags=4163<UP,...": the old slice [x+6:y-1]
  # dropped its last digit ("416"), so neither case below ever matched and
  # check_eth0 never did anything (2026-11-05).
  m = re.search(r'flags=(\d+)<', net_stats[1])
  if m:
      if True:
          a = m.group(1)
          if a == '4099':
              return(0)				#were not connected so we just return ok
          elif a == '4163':
             if has_ipv4("eth0"):
                 return(0)                      #we have an IPv4 address so were good to go
             # Cable in but no IPv4 address.  (2026-11-05: eth0's dhclient
             # had died and the lease ran out overnight; the old test looked
             # for "inet", which also matched inet6 and the lines of the
             # interfaces after eth0, so it never saw it.)  A running dhclient
             # is still asking for a lease: leave it.  Otherwise restart eth0
             # in the background (ifup waits up to a minute for a lease, which
             # would hold up the USB checks), at most every 5 minutes.
             if eth0_dhclient_running():
                 return(0)
             if time.time() - eth0_restart[0] > 300:
                 eth0_restart[0] = time.time()
                 logger.info("eth0 is connected but has no IPv4 address and no DHCP client: restarting eth0")
                 try:
                     subprocess.Popen(['sh', '-c', 'ifdown eth0; ifup eth0'],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                 except Exception:
                     pass
             return(1)
          return(1)				#were in some wierd mode so we error
      return(1)					#we cant find the flags
  return(1)

def check_wlan_CI(CI):
  """
  Check whether the Client Interface wlan is present in the ifconfig output.

  A simple presence check -- if wlan<CI> appears in ``ifconfig`` output at all,
  the interface exists (even if it has no IP yet).  Used by getNetworkClass() to
  decide whether to bring the CI interface up.

  Parameters:
      CI (int | str): The wlan number of the Client Interface (e.g. 1 for wlan1).

  Returns:
      int: 0 if wlan<CI> is found in ifconfig output (interface exists),
           1 if wlan<CI> is not found (interface absent or not yet up).
  """
  process = Popen("ifconfig", shell=False, stdout=PIPE, stderr=PIPE)
  stdout, stderr = process.communicate()
  net_stats = str(stdout).split("wlan"+str(CI))   # look for wlan(CI) in ifconfig output
  if (len(net_stats)==1):     # wlan(CI) not found - return 1
    return(1)
  else:
    return(0)                 # wlan(CI) found... return 0


ci_restart = [0.0]            # time of check_stat_CI's last client restart

def check_stat_CI(CI):
    """
    Check the Client Interface link state and attempt recovery if it has dropped.

    Called on every 10th main-loop iteration alongside check_eth0().  Unlike
    check_wlan_CI() which only tests presence, this function also inspects the
    interface flags to detect a link that is up but has lost its association
    (flags != 4163, or no "inet" address).

    Logic:
        1. If check_CI() returns 0 (no SSID configured in wpa_supplicant), skip all
           checks and return 0 -- there is nothing to connect to.
        2. Parse ifconfig output for wlan<CI>.  If the interface is absent (no split
           result), return 0 (nothing to fix).
        3. If the flags field is present but not 4163 (RUNNING), set z=1 to indicate
           a recovery is needed.
        4. If z != 0, issue ifdown/ifup on wlan<CI> and return 0 on success or 1 on
           failure.

    Parameters:
        CI (int | str): The wlan number of the Client Interface (e.g. 1 for wlan1).

    Returns:
        int: 0 if the CI is healthy, unconfigured, or was successfully recovered,
             1 if the ifdown/ifup recovery attempt failed.
    """
    if (check_CI() == 0):
        return(0)	      #Were ok because we have not SSID set
    # (2026-11-05) The old test read the ifconfig flags with a slice that
    #  never matched, so it never restarted anything; on the CM4 wlan0 stayed
    #  down after a failed ifup at boot ("ifup: failed to bring up wlan0",
    #  stale wpa_supplicant control socket).  Now: restart the client only
    #  when it is administratively down or its wpa_supplicant does not answer
    #  -- not when it is simply not connected (out of range, wrong password),
    #  which wpa_supplicant keeps retrying by itself -- in the background and
    #  at most every 5 minutes.
    dev = "wlan" + str(CI)
    try:
        with open("/sys/class/net/" + dev + "/flags") as f:
            flags = int(f.read().strip(), 16)
    except (OSError, ValueError):
        return(0)                         # no such interface: nothing to fix
    up = bool(flags & 0x1)
    try:
        wpa_ok = subprocess.run(["wpa_cli", "-i", dev, "status"], stdout=PIPE, stderr=PIPE,
                                timeout=10).returncode == 0
    except Exception:
        wpa_ok = True                     # cannot tell: do not restart
    if up and wpa_ok:
        return(0)
    if time.time() - ci_restart[0] < 300:
        return(1)
    ci_restart[0] = time.time()
    logger.info("Client " + dev + " is " + ("up" if up else "down") + (", wpa_supplicant answers" if wpa_ok else ", wpa_supplicant does not answer") + ": restarting " + dev)
    try:
        subprocess.Popen(["sh", "-c", "ifdown %s; rm -f /var/run/wpa_supplicant/%s; ifup %s" % (dev, dev, dev)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return(1)
    return(0)


# ---------------------------------------------------------------------------
# Remembered client Wi-Fi networks (2026-11-05, Kirk)
#
# The admin page sets one client network: the first network={} block of
# wpa_supplicant.conf (connectbox-manage changes only that block).  When the
# client interface is connected to a network AND the internet works through
# that interface, the network's block is remembered in KNOWN_WIFI_FILE (newest
# first, at most KNOWN_WIFI_MAX; a new one drops the oldest, a known one that
# connects again moves to the top).  The remembered networks other than the
# admin's own are written after the KNOWN_WIFI_MARK line at the end of
# wpa_supplicant.conf, so wpa_supplicant connects by itself to whichever of them
# is in range.  Everything from the marker line to the end of the file is
# rewritten by PxUSBm; everything before it is left exactly as it is.
# Passwords (psk lines) are never logged.
# ---------------------------------------------------------------------------
KNOWN_WIFI_FILE = '/etc/wpa_supplicant/connectbox_known_wifi.json'   # root only (0600)
KNOWN_WIFI_MAX = 10
WPA_CONF = '/etc/wpa_supplicant/wpa_supplicant.conf'
KNOWN_WIFI_MARK = '# Remembered by PxUSBm'
BUILD_MARKER = '/run/connectbox-build'          # set while the playbook runs
INTERNET_TEST_URL = 'http://connectivitycheck.gstatic.com/generate_204'
INTERNET_TEST_TABLE = '129'                      # routing table used only by the test
KNOWN_WIFI_RETRY = 300                           # seconds before testing a failed network again
known_wifi_state = {'tested': {}, 'conf_written': 0.0, 'last_ssid': None, 'last_seen': 0.0,
                    'dhcp_refresh': 0.0, 'stale_logged': False}


def wpa_parse(text):
    """Split wpa_supplicant.conf text into (own, blocks).

    own is the text before the KNOWN_WIFI_MARK line (or all of it);
    blocks is a list of the network={} blocks in own, each a list of the
    stripped lines inside the braces, in file order."""
    own = text.split('\n' + KNOWN_WIFI_MARK)[0] if ('\n' + KNOWN_WIFI_MARK) in text else text
    if text.startswith(KNOWN_WIFI_MARK):
        own = ''
    blocks = []
    cur = None
    for line in own.split('\n'):
        s = line.strip()
        if cur is None:
            if s.replace(' ', '').startswith('network={'):
                cur = []
        elif s == '}':
            blocks.append(cur)
            cur = None
        elif s and not s.startswith('#'):
            cur.append(s)
    return own, blocks


def wpa_block_ssid(lines):
    """The ssid= value of a block exactly as written (e.g. '"Wilson1"'), or None."""
    for s in lines:
        if s.startswith('ssid='):
            return s[5:]
    return None


def wpa_ssid_text(value):
    """The SSID as wpa_cli prints it, for a quoted ssid= value (None for hex)."""
    if value and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return None


def known_wifi_load():
    try:
        with open(KNOWN_WIFI_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            ok = []
            for e in data:
                if isinstance(e, dict) and isinstance(e.get('key'), str) and isinstance(e.get('lines'), list) and \
                        all(isinstance(l, str) and '\n' not in l and '{' not in l and '}' not in l for l in e['lines']):
                    ok.append(e)
            return ok
    except Exception:
        pass
    return []


def write_private(path, text, mode=0o600, like=None):
    """Write text to path through a temporary file (no half-written file).
    The file gets the mode of 'like' if it exists, otherwise 'mode'."""
    tmp = path + '.pxusbm-tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    if like and os.path.exists(like):
        shutil.copymode(like, tmp)
        st = os.stat(like)
        os.chown(tmp, st.st_uid, st.st_gid)
    else:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def known_wifi_save(entries):
    d = os.path.dirname(KNOWN_WIFI_FILE)
    if not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    write_private(KNOWN_WIFI_FILE, json.dumps(entries, indent=1) + '\n', mode=0o600)


def known_wifi_conf_text(own, own_blocks, entries):
    """wpa_supplicant.conf text: 'own' unchanged, then the remembered networks
    that are not already in it, after the marker line."""
    own_keys = set(wpa_block_ssid(b) for b in own_blocks)
    extra = [e for e in entries if e['key'] not in own_keys]
    if not extra:
        return own.rstrip('\n') + '\n'
    out = own.rstrip('\n') + '\n\n' + KNOWN_WIFI_MARK + \
        ' (networks that connected with internet, newest first; rewritten automatically)\n'
    for e in extra:
        out += 'network={\n' + ''.join('\t' + s + '\n' for s in e['lines']) + '}\n'
    return out


def wpa_status(ci):
    """wpa_cli status of wlan<ci> as a dict ({} if wpa_cli fails)."""
    try:
        r = subprocess.run(['wpa_cli', '-i', 'wlan' + str(ci), 'status'],
                           stdout=PIPE, stderr=PIPE, timeout=10)
        st = {}
        for line in r.stdout.decode('utf-8', 'replace').split('\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                st[k.strip()] = v.strip()
        return st
    except Exception:
        return {}


def has_ipv4(dev):
    """True if dev has an IPv4 address (ifconfig's 'inet' also matched inet6)."""
    try:
        r = subprocess.run(['ip', '-4', '-o', 'addr', 'show', 'dev', dev],
                           stdout=PIPE, stderr=PIPE, timeout=10)
        return ' inet ' in r.stdout.decode('utf-8', 'replace')
    except Exception:
        return False


def lease_gateway(dev):
    """The router of dev's newest dhclient lease, or None."""
    gw = None
    try:
        with open('/var/lib/dhcp/dhclient.%s.leases' % dev, 'r') as f:
            for m in re.finditer(r'option routers ([0-9.]+)', f.read()):
                gw = m.group(1)
    except Exception:
        pass
    return gw


def internet_through(dev):
    """True if the internet answers through dev itself.

    While eth0 has the default route, the client interface has none (its
    DHCP default route is refused as a duplicate), so a plain
    'curl --interface' fails.  For the test only, add a default route via
    dev's own DHCP router in a separate table, used only by sockets bound to
    dev, and remove it afterwards.  Other traffic is not affected."""
    gw = lease_gateway(dev)
    if not gw:
        logger.info("Remembered Wi-Fi: no DHCP router known for " + dev)
        return False
    rule = ['ip', 'rule', 'add', 'oif', dev, 'lookup', INTERNET_TEST_TABLE, 'priority', INTERNET_TEST_TABLE]
    try:
        subprocess.run(['ip', 'route', 'replace', 'default', 'via', gw, 'dev', dev,
                        'table', INTERNET_TEST_TABLE], stdout=PIPE, stderr=PIPE, timeout=10)
        subprocess.run(rule, stdout=PIPE, stderr=PIPE, timeout=10)
        r = subprocess.run(['curl', '-s', '-m', '10', '-o', '/dev/null', '-w', '%{http_code}',
                            '--interface', dev, INTERNET_TEST_URL],
                           stdout=PIPE, stderr=PIPE, timeout=15)
        return r.stdout.decode('utf-8', 'replace').strip() == '204'
    except Exception as e:
        logger.info("Remembered Wi-Fi: internet test failed to run: " + str(e))
        return False
    finally:
        try:
            rule[2] = 'del'
            subprocess.run(rule, stdout=PIPE, stderr=PIPE, timeout=10)
            subprocess.run(['ip', 'route', 'flush', 'table', INTERNET_TEST_TABLE],
                           stdout=PIPE, stderr=PIPE, timeout=10)
        except Exception:
            pass


def check_known_wifi(ci):
    """Remember the connected client network and keep the remembered ones in
    wpa_supplicant.conf.  Called about every 60 s from the main loop."""
    if ci == "" or os.path.exists(BUILD_MARKER):
        return
    dev = 'wlan' + str(ci)
    st = known_wifi_state
    try:
        with open(WPA_CONF, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return
    own, own_blocks = wpa_parse(text)
    entries = known_wifi_load()
    changed = False

    status = wpa_status(ci)
    ssid_now = status.get('ssid') if status.get('wpa_state') == 'COMPLETED' else None

    # Moved to another network by itself: the DHCP lease is still the old
    # network's, so renew it by restarting the interface (at most every 5 min).
    #  Not when wpa_supplicant itself was restarted (admin page, ifup): its
    #  ifup started a new DHCP client too.
    try:
        wpa_started = os.path.getmtime('/run/wpa_supplicant.%s.pid' % dev)
    except Exception:
        wpa_started = 0.0
    if ssid_now and st['last_ssid'] and ssid_now != st['last_ssid'] and \
            wpa_started < st['last_seen'] and time.time() - st['dhcp_refresh'] > 300:
        logger.info("Client Wi-Fi moved from " + st['last_ssid'] + " to " + ssid_now + ": renewing DHCP on " + dev)
        st['dhcp_refresh'] = time.time()
        try:
            subprocess.Popen(['sh', '-c', 'ifdown %s; ifup %s' % (dev, dev)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        st['last_ssid'] = ssid_now
        return
    if ssid_now:
        st['last_ssid'] = ssid_now
    st['last_seen'] = time.time()

    if ssid_now:
        # The block wpa_supplicant is using: network id N is the N-th block in
        # the file it read.  Skip if the file changed after wpa_supplicant read
        # it (e.g. a new password typed on the admin page and not yet applied):
        # the block in the file may not be the one that connected.
        loaded = max(st['conf_written'], wpa_started)
        try:
            fresh = os.path.getmtime(WPA_CONF) <= loaded + 1
        except Exception:
            fresh = False
        _, all_blocks = wpa_parse(text.replace('\n' + KNOWN_WIFI_MARK, '\n#'))
        block = None
        try:
            block = all_blocks[int(status.get('id', '-1'))]
        except (ValueError, IndexError):
            block = None
        if block is not None and wpa_ssid_text(wpa_block_ssid(block)) not in (None, ssid_now):
            block = None                       # id and SSID disagree: file changed
        if not fresh:
            if not st['stale_logged']:
                logger.info("Remembered Wi-Fi: wpa_supplicant.conf changed since it was read; not learning " + ssid_now + " yet")
                st['stale_logged'] = True
            block = None
        else:
            st['stale_logged'] = False
        if block is not None and wpa_block_ssid(block):
            key = wpa_block_ssid(block)
            top = entries[0] if entries else None
            if not (top and top['key'] == key and top['lines'] == block):
                last = st['tested'].get(key, 0)
                if time.time() - last > KNOWN_WIFI_RETRY and has_ipv4(dev):
                    if internet_through(dev):
                        entries = [e for e in entries if e['key'] != key]
                        entries.insert(0, {'key': key, 'ssid': ssid_now, 'lines': block,
                                           'added': time.strftime('%Y-%m-%d %H:%M:%S')})
                        dropped = entries[KNOWN_WIFI_MAX:]
                        entries = entries[:KNOWN_WIFI_MAX]
                        changed = True
                        st['tested'].pop(key, None)
                        logger.info("Remembered Wi-Fi: " + ssid_now + " connected with internet; saved at the top of the list (" + str(len(entries)) + " networks)")
                        for e in dropped:
                            logger.info("Remembered Wi-Fi: list full, dropped " + str(e.get('ssid')))
                    else:
                        st['tested'][key] = time.time()
                        logger.info("Remembered Wi-Fi: " + ssid_now + " connected but no internet through " + dev + "; not saved")

    if changed:
        try:
            known_wifi_save(entries)
        except Exception as e:
            logger.info("Remembered Wi-Fi: could not save the list: " + str(e))
    else:
        # Read the list again just before writing: the admin page's "wipe"
        # (connectbox-manage) may have removed it while this check ran.
        entries = known_wifi_load()
    new_text = known_wifi_conf_text(own, own_blocks, entries)
    if new_text != text and new_text.rstrip('\n') != text.rstrip('\n'):
        try:
            write_private(WPA_CONF, new_text, like=WPA_CONF)
            st['conf_written'] = os.path.getmtime(WPA_CONF)
            subprocess.run(['wpa_cli', '-i', dev, 'reconfigure'], stdout=PIPE, stderr=PIPE, timeout=10)
            logger.info("Remembered Wi-Fi: wpa_supplicant.conf updated, " +
                        str(len([e for e in entries if e['key'] not in set(wpa_block_ssid(b) for b in own_blocks)])) +
                        " remembered networks after the admin's own")
        except Exception as e:
            logger.info("Remembered Wi-Fi: could not update wpa_supplicant.conf: " + str(e))


# ---------------------------------------------------------------------------
# Internet sharing (2026-11-05, Kirk): an Advanced switch on the admin page
# (brand.j2 "internet_sharing", default 0).  When it is 1, phones on the
# ConnectBox Wi-Fi reach the internet through whichever uplink the box has
# (eth0 or the client Wi-Fi): IPv4 forwarding on, NAT (masquerade) of the AP
# network out of every other interface, and DNS answered by real servers
# instead of the box's "every name is the box" answer (the captive portal
# names wi.fi, gowifi.org, ... and connectbox still go to the box).  No filtering.
# When it is 0 (or missing) everything is put back: forwarding off, the
# chains removed, dnsmasq.conf as built.  Checked about every 30 s, so the
# setting also survives reboots, and only changes what differs.
#   iptables: chains CB_SHARE (filter, jumped to from FORWARD) and
#   CB_SHARE_NAT (nat, from POSTROUTING); the persistent rules (FORWARD DROP)
#   are not changed.
#   dnsmasq.conf: address= lines that point names somewhere other than the box
#   (address=/#/... and the phones' connectivity-check overrides) get the
#   SHARING_TAG prefix, and a server= block from /etc/resolv.conf is added at
#   the end; both are undone when sharing is off.
# ---------------------------------------------------------------------------
SHARING_KEY = 'internet_sharing'
DNSMASQ_CONF = '/etc/dnsmasq.conf'
SHARING_TAG = '#CB-internet-sharing# '
SHARING_BEGIN = '# BEGIN CONNECTBOX INTERNET SHARING (PxUSBm)'
SHARING_END = '# END CONNECTBOX INTERNET SHARING'
SHARING_FALLBACK_DNS = ['1.1.1.1', '8.8.8.8']
# Names that must still reach the box while sharing is on (the captive portal
# names wi.fi, gowifi.org, ... and the box's own): the server_name lines of
# the ConnectBox nginx sites and the box's host name, plus these in case
# those cannot be read.
SHARING_LOCAL_NAMES = ['wi.fi', 'gowifi.org', 'gowifi.com', 'go', 'connectbox']
NGINX_SITES = '/etc/nginx/sites-enabled'
sharing_state = {'on': None, 'error_logged': False}


def brand_value(key, default=0):
    """A brand.j2 value, key matched without regard to case."""
    try:
        with open('/usr/local/connectbox/brand.j2', 'r', encoding='utf-8') as f:
            brand = json.loads(f.read())
        for k, v in brand.items():
            if k.lower() == key.lower():
                return v
    except Exception:
        pass
    return default


def ap_address(dev):
    """(address, network) of dev's own IPv4 address, e.g. ('10.129.0.1', '10.0.0.0/8'), or (None, None).

    Skips labelled extra addresses such as the captive portal's
    172.217.3.174/24 on wlan1:0: after a reboot ip listed that one first and
    sharing was set up for 172.217.3.0/24, so phones got no NAT and the box's
    names pointed at 172.217.3.174 (2026-11-05).  Of the box's own addresses
    the widest network is used (10.129.0.1/8 from dhcpcd and /16 from ifupdown
    are both there)."""
    try:
        import ipaddress
        r = subprocess.run(['ip', '-4', '-o', 'addr', 'show', 'dev', dev],
                           stdout=PIPE, stderr=PIPE, timeout=10)
        best = None
        for line in r.stdout.decode('utf-8', 'replace').split('\n'):
            words = line.split('valid_lft')[0].replace('\\', ' ').split()
            if 'inet' not in words or words.index('inet') + 1 >= len(words):
                continue
            if ':' in words[-1]:
                continue                          # labelled extra address, e.g. wlan1:0
            iface = ipaddress.ip_interface(words[words.index('inet') + 1])
            if best is None or iface.network.prefixlen < best.network.prefixlen:
                best = iface
        if best is not None:
            return str(best.ip), str(best.network)
    except Exception:
        pass
    return None, None


def upstream_dns(ap_ip):
    """IPv4 name servers from /etc/resolv.conf (the uplink's, from DHCP),
    without loopback or the box itself; the fallback servers if none."""
    servers = []
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                m = re.match(r'\s*nameserver\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s*$', line)
                if m and not m.group(1).startswith('127.') and m.group(1) != ap_ip \
                        and m.group(1) not in servers:
                    servers.append(m.group(1))
    except Exception:
        pass
    return servers or list(SHARING_FALLBACK_DNS)


def box_names():
    """Host names served by the box's nginx sites (no '_', no '.local'
    wildcards), plus SHARING_LOCAL_NAMES; lower case, each once."""
    names = []
    try:
        for fn in sorted(os.listdir(NGINX_SITES)):
            if not fn.startswith('connectbox'):
                continue
            with open(os.path.join(NGINX_SITES, fn), 'r', encoding='utf-8', errors='replace') as f:
                for m in re.finditer(r'^\s*server_name\s+([^;]*);', f.read(), re.M):
                    names += m.group(1).split()
    except Exception:
        pass
    try:
        import socket
        names.append(socket.gethostname())
    except Exception:
        pass
    out = []
    for n in names + SHARING_LOCAL_NAMES:
        n = n.lower()
        if n != '_' and not n.startswith('.') and re.match(r'^[a-z0-9.-]+$', n) and n not in out:
            out.append(n)
    return out


def dnsmasq_sharing_text(text, on, ap_ip, servers, local_names=()):
    """dnsmasq.conf text for sharing on/off (off gives back the built file)."""
    out = []
    inblock = False
    for line in text.split('\n'):
        if line.startswith(SHARING_BEGIN):
            inblock = True
            continue
        if inblock:
            if line.startswith(SHARING_END):
                inblock = False
            continue
        if line.startswith(SHARING_TAG):
            line = line[len(SHARING_TAG):]
        out.append(line)
    if on:
        for i, line in enumerate(out):
            m = re.match(r'\s*address=/([^/]*)/([^\s#]*)', line)
            if m and (m.group(1) == '#' or m.group(2) != ap_ip):
                out[i] = SHARING_TAG + line
        while out and out[-1] == '':
            out.pop()
        out += [SHARING_BEGIN,
                '# Internet sharing is on (admin page): names are looked up on these servers.',
                '# PxUSBm removes this block and the ' + SHARING_TAG.strip() + ' marks when it is off.']
        out += ['address=/%s/%s' % (n, ap_ip) for n in local_names]
        out += ['server=' + s for s in servers]
        out += [SHARING_END, '']
    return '\n'.join(out)


def ipt(args):
    """Run iptables with args; return its exit code."""
    try:
        return subprocess.run(['iptables'] + args, stdout=PIPE, stderr=PIPE, timeout=15).returncode
    except Exception:
        return -1


def sharing_rules_ok(on, ap, ap_net):
    """True if the iptables state matches on/off."""
    jumps = (ipt(['-C', 'FORWARD', '-j', 'CB_SHARE']) == 0 and
             ipt(['-t', 'nat', '-C', 'POSTROUTING', '-j', 'CB_SHARE_NAT']) == 0)
    if not on:
        return not jumps and ipt(['-n', '-L', 'CB_SHARE']) != 0 and \
            ipt(['-t', 'nat', '-n', '-L', 'CB_SHARE_NAT']) != 0
    return jumps and \
        ipt(['-C', 'CB_SHARE', '-i', ap, '!', '-o', ap, '-j', 'ACCEPT']) == 0 and \
        ipt(['-C', 'CB_SHARE', '-o', ap, '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']) == 0 and \
        ipt(['-t', 'nat', '-C', 'CB_SHARE_NAT', '-s', ap_net, '!', '-o', ap, '-j', 'MASQUERADE']) == 0


# Data passed through internet sharing (2026-11-05, Kirk): byte counters of
# the two CB_SHARE rules (phones -> internet = up, internet -> phones = down)
# added to a running total in USAGE_FILE, kept across reboots.  The file also
# keeps the counter values already counted (and the boot they belong to), so
# a PxUSBm restart does not count them twice.  The admin page's Reset
# (connectbox-manage) sets up/down to 0 and leaves the counter values.
# Read by the admin page and the front panel.
USAGE_FILE = '/usr/local/connectbox/internet_usage.json'


def sharing_counters():
    """(up, down) bytes of the CB_SHARE rules, or None when there are none."""
    try:
        r = subprocess.run(['iptables', '-L', 'CB_SHARE', '-v', '-x', '-n'],
                           stdout=PIPE, stderr=PIPE, timeout=15)
        if r.returncode != 0:
            return None
        up = down = None
        for line in r.stdout.decode('utf-8', 'replace').split('\n')[2:]:
            f = line.split()
            if len(f) >= 3 and f[2] == 'ACCEPT':
                if 'ESTABLISHED' in line:
                    down = int(f[1])
                else:
                    up = int(f[1])
        if up is None or down is None:
            return None
        return up, down
    except Exception:
        return None


def boot_id():
    try:
        with open('/proc/sys/kernel/random/boot_id') as f:
            return f.read().strip()
    except Exception:
        return ''


def usage_load():
    u = {}
    try:
        with open(USAGE_FILE, 'r', encoding='utf-8') as f:
            u = json.load(f)
    except Exception:
        pass
    if not isinstance(u, dict):
        u = {}
    for k in ('up', 'down', 'counter_up', 'counter_down'):
        try:
            u[k] = max(0, int(u.get(k, 0)))
        except Exception:
            u[k] = 0
    u.setdefault('since', time.strftime('%Y-%m-%d %H:%M'))
    return u


def update_usage(counters_reset=False):
    """Add what the CB_SHARE counters counted since last time to the total.
    counters_reset: the rules are about to be rebuilt (their counters start
    again at 0)."""
    try:
        before = None
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                before = f.read()
        u = usage_load()
        if u.get('boot_id') != boot_id():          # new boot: the rules are new
            u['boot_id'] = boot_id()
            u['counter_up'] = u['counter_down'] = 0
        c = sharing_counters()
        if c is not None:
            up, down = c
            u['up'] += up - u['counter_up'] if up >= u['counter_up'] else up
            u['down'] += down - u['counter_down'] if down >= u['counter_down'] else down
            u['counter_up'], u['counter_down'] = up, down
        if counters_reset or c is None:
            u['counter_up'] = u['counter_down'] = 0
        text = json.dumps(u, indent=1, sort_keys=True) + '\n'
        if text != before:
            if before is None and u['up'] == 0 and u['down'] == 0 and c is None:
                return                              # nothing to record yet
            write_private(USAGE_FILE, text, mode=0o644)
    except Exception as e:
        logger.info("Internet sharing: could not update the data total: " + str(e))


def set_sharing_rules(on, ap, ap_net):
    while ipt(['-D', 'FORWARD', '-j', 'CB_SHARE']) == 0:
        pass
    while ipt(['-t', 'nat', '-D', 'POSTROUTING', '-j', 'CB_SHARE_NAT']) == 0:
        pass
    for table, chain in (('filter', 'CB_SHARE'), ('nat', 'CB_SHARE_NAT')):
        ipt(['-t', table, '-F', chain])
        ipt(['-t', table, '-X', chain])
    if on:
        ipt(['-N', 'CB_SHARE'])
        ipt(['-A', 'CB_SHARE', '-i', ap, '!', '-o', ap, '-j', 'ACCEPT'])
        ipt(['-A', 'CB_SHARE', '-o', ap, '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'])
        ipt(['-I', 'FORWARD', '1', '-j', 'CB_SHARE'])
        ipt(['-t', 'nat', '-N', 'CB_SHARE_NAT'])
        ipt(['-t', 'nat', '-A', 'CB_SHARE_NAT', '-s', ap_net, '!', '-o', ap, '-j', 'MASQUERADE'])
        ipt(['-t', 'nat', '-I', 'POSTROUTING', '1', '-j', 'CB_SHARE_NAT'])


def ip_forward(value=None):
    path = '/proc/sys/net/ipv4/ip_forward'
    try:
        if value is not None:
            with open(path, 'w') as f:
                f.write('1\n' if value else '0\n')
        with open(path, 'r') as f:
            return f.read().strip() == '1'
    except Exception:
        return None


def disconnect_ap_stations(ap):
    """Deauthenticate every phone on the AP (they rejoin by themselves)."""
    if not shutil.which('hostapd_cli'):
        return
    try:
        r = subprocess.run(['hostapd_cli', '-i', ap, 'list_sta'], stdout=PIPE, stderr=PIPE, timeout=10)
        macs = [l.strip() for l in r.stdout.decode('utf-8', 'replace').split('\n')
                if re.match(r'^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$', l.strip())]
        for mac in macs:
            subprocess.run(['hostapd_cli', '-i', ap, 'deauthenticate', mac], stdout=PIPE, stderr=PIPE, timeout=10)
        logger.info("Internet sharing: asked " + str(len(macs)) + " phone(s) on " + ap + " to rejoin")
    except Exception as e:
        logger.info("Internet sharing: could not disconnect the phones: " + str(e))


def check_internet_sharing():
    """Make forwarding, NAT and DNS match brand.j2 internet_sharing."""
    st = sharing_state
    try:
        on = str(brand_value(SHARING_KEY, 0)).strip() in ('1', 'true', 'True')
        ap = 'wlan' + str(get_AP())
        ap_ip, ap_net = ap_address(ap)
        if on and not ap_ip:
            if not st['error_logged']:
                logger.info("Internet sharing: " + ap + " has no IPv4 address yet; waiting")
                st['error_logged'] = True
            return
        st['error_logged'] = False
        switched = st['on'] is not None and st['on'] != on    # changed while running
        if st['on'] != on:
            logger.info("Internet sharing is " + ("ON: phones on the ConnectBox Wi-Fi can reach the internet through the box's uplink" if on else "off"))
            st['on'] = on

        # IPv4 forwarding
        if on and ip_forward() is not True:
            ip_forward(True)
        elif not on and ip_forward() is True:
            ip_forward(False)

        # iptables (count what the rules passed before they change)
        if not sharing_rules_ok(on, ap, ap_net):
            update_usage(counters_reset=True)
            set_sharing_rules(on, ap, ap_net)
            if sharing_rules_ok(on, ap, ap_net):
                logger.info("Internet sharing: firewall rules " + ("added for " + ap_net + " on " + ap if on else "removed"))
                st['rules_error'] = False
            elif not st.get('rules_error'):
                logger.info("Internet sharing: could not set the firewall rules (iptables)")
                st['rules_error'] = True
        else:
            update_usage()

        # DNS
        with open(DNSMASQ_CONF, 'r', encoding='utf-8') as f:
            text = f.read()
        new = dnsmasq_sharing_text(text, on, ap_ip, upstream_dns(ap_ip) if on else [],
                                   box_names() if on else [])
        if new != text:
            write_private(DNSMASQ_CONF, new, like=DNSMASQ_CONF)
            r = subprocess.run(['systemctl', 'restart', 'dnsmasq'], stdout=PIPE, stderr=PIPE, timeout=60)
            logger.info("Internet sharing: dnsmasq.conf " + ("set to real DNS" if on else "back to offline DNS") +
                        ", dnsmasq restarted (" + str(r.returncode) + ")")
        if switched:
            # Phones decide "this Wi-Fi has internet" when they join.  After
            # sharing was turned off, an Android phone that still believed it
            # had internet sent its traffic over mobile data and could not
            # reach the box until it rejoined (2026-11-05): disconnect the
            # phones so they rejoin and check again.
            disconnect_ap_stations(ap)
    except Exception as e:
        logger.info("Internet sharing check failed: " + str(e))


def checkServices():
    """
    Verify that all critical network services started correctly after boot and
    attempt to restart any that are not active.

    Called once (twice with a 5-second gap) after the initial startup delay to
    catch services that failed to start during boot -- a common occurrence on
    embedded hardware where the network interfaces may not be ready when systemd
    first tries to bring them up.

    Services checked in order:
        1. networking.service  -- the base networking stack; without it nothing works.
        2. hostapd             -- the Access Point daemon; if masked, unmask then
                                  restart.  If simply stopped, restart it.
        3. ifup@<AP>           -- the systemd instance that brought up the AP wlan;
                                  if not active, restart it and then restart hostapd
                                  so it re-binds to the newly-up interface.
        4. ifup@eth0           -- the wired Ethernet interface instance.
        5. ifup@<CI>           -- the Client Interface wlan instance; only checked if
                                  check_CI() confirms a real SSID is configured.

    For each service, the pattern is: check -> restart if needed -> check again ->
    return 1 (error) if still not running.  The caller (main block) calls this
    function twice with a 5-second sleep between attempts before giving up and
    continuing anyway, since a permanently broken network state is handled by the
    periodic checks in the main loop.

    Returns:
        int: 0 if all checked services are active (or were successfully restarted),
             1 if any service could not be brought to active state.
    """
    print("starting Check Services")
    logger.info("check services starting")
    process = Popen(["/bin/systemctl",'status','networking'], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    # Still starting is not failed: wait for it (up to 2 minutes) before
    #  deciding.  On Raspberry Pi OS networking.service is still activating
    #  here, and restarting it then deadlocked with the AP's ifup (its pre-up
    #  wifi_configurator restarts hostapd, which waited for the networking
    #  stop, which waited for that ifup) - CM4, 2026-11-04.
    waited = 0
    while serva.find("Active: activating") >= 0 and waited < 120:
        time.sleep(5)
        waited += 5
        process = Popen(["/bin/systemctl",'status','networking'], shell = False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        serva = str(stdout)
    if waited:
        logger.info("networking.service was still starting; waited "+str(waited)+" s")
    x = serva.find("Active: active")
    print("looking for networking.serice : "+str(x))
    if x < 0:
        print("Found networking not running")
        logger.info("Found networking not running")
        try:
            print("well have to retry the networking.service")
            logger.info("well we have to retry the networking.service")
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
            logger.info("OK we restarted the networking.service and were running")
            pass
        else:
            logger.info("OK we restarted the networking.service and were not running still")
            return(1)
        #we will continue aas we have a working networking service
        #We want to check the AP to make sure its up
    else:
        print("networking service running nicely")
        logger.info("Networking service was running nicely")

    logger.info("starting to test AP services")
    # At boot the AP's ifup (ifup@wlanX.service) runs wifi_configurator, which
    #  scans, writes hostapd.conf and starts hostapd.  Starting hostapd here
    #  while it scans made the scan fail ("Device or resource busy") and the
    #  channel was chosen blind (2026-11-05): wait for that ifup first.
    ap_unit = "ifup@wlan" + str(get_AP()) + ".service"
    for i in range(45):
      state = subprocess.run(["/bin/systemctl", "is-active", ap_unit], stdout=PIPE, stderr=PIPE).stdout.decode().strip()
      if state != "activating":
        break
      if i == 0:
        logger.info("Waiting for " + ap_unit + " (wifi_configurator) before checking hostapd")
      time.sleep(2)
    process = Popen(["/bin/systemctl","status", "hostapd"], shell=False, stdout=PIPE, stderr=PIPE) 
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    if x < 0:
      #We got here because the hostapd service is not running
      x = serva.find("Loaded: masked")
      if x >= 0:
        #Ok we have encountered hostapd masked for whatever reason
        logger.info("hostapd is masked and needs to be unmasked")
        process = Popen(['/bin/systemctl', 'unmask', 'hostapd'], shell =False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if stderr != "":
          logger.info("tried to unmask hostapd but got an error.  Don't know what to do now.")
      os.system("/bin/systemctl reset-failed hostapd 2>/dev/null")   # a failed hostapd may be rate-limited
      process = Popen(['/bin/systemctl', 'restart', 'hostapd'], shell=False, stdout=PIPE, stderr= PIPE)
      stdout, stderr = process.communicate()
      serva = str(stdout)
      if serva.find("Active: active") >= 0:
        logger.info("well the restart worked and is no longer masked")
        logger.info("hostapd may still have isseus but this is good")
      else:
        logger.info("tried to restart Hostapd but still didn't get an active service.  Don't know what to do now.")
    # hostapd can be active and ENABLED with the radio not set up (no
    #  channel, txpower -100 dBm, no beacon): seen after the first start at
    #  boot on the CM4's 8812au (2026-11-05).  One restart fixes it.
    time.sleep(5)
    if not ap_really_up("wlan" + str(get_AP())):
      logger.info("hostapd is running but the AP radio is not set up: restarting hostapd")
      restart_hostapd()
    AP = "wlan"+str(get_AP())
    process = Popen(["/bin/systemctl",'status','ifup@'+AP], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    print("looking for ifup@AP.serice : "+AP+"and line is "+str(x))
    if x < 0:									#we found our AP ifup service not active
        print("Found the ifup@AP.service not running")
        logger.info("Found the ifup@AP.service not running")
        try:
            print("Going to have to try to restart the ifup@AP.service")
            logger.info("Going to have to try to restart the ifup@AP.service")
            os.system("/bin/systemctl restart ifup@"+AP)
            process = Popen(["/bin/systemctl","status","ifup@"+AP], shell=False, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            serva = str(stdout)
            x = serva.find("Active: active")
            if x > 0:
                try:
                    os.system("/bin/systemctl restart hostapd")
                    print("Ok we have succeeded in restarting ifup@AP.serice and have restarted hostapd as well")
                    logger.info("Ok we have succeded in restarting ifup@AP.service and have restarted hostapd as well")
                    pass
                except:
                    return(1) #We failed on the restart of hostapd after restarting wlanAP
                    logger.info("We failed on the restart of hostapd.service")
        except:
           logger.info("We failed on the restart of ifup@AP.service")
           return(1)								#We errored out on the retry of starting the ifup@AP service

       # If we are here then we have an ifup@AP that is loaded active and we fixed it.
    else:
        logger.info("We are loaded and active on ifup@AP.service")
        print("were loaded and running on the ifup@AP.service")


    # If we are here then we have an ifup@CI that is loaded active and we fixed it or CI is null so we skipped testing
    # now we need to test for our last item which is eth0

    logger.info("Strting the ifup@etho0.service test")
    process = Popen(["/bin/systemctl",'status','ifup@eth0'], shell = False, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    serva = str(stdout)
    x = serva.find("Active: active")
    if x < 0:									#we found our AP ifup service
        print("Ok we found the ifup@eth0.service not running")
        logger.info("Ok we found an ifup@eth0.service not running")
        try:
            print("Ok were going to try restarting the ifup@eth0.service")
            logger.info("OK we are going to try restarting the ifup@eth0.service")
            os.system("/bin/systemctl restart ifup@eath0")
            process = Popen(["/bin/systemctl","status","ifup@eath0"], shell=False, stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            serva = str(stdout)
            x = serva.find("Active: active")
            if x > 0:
                print("Well we succeeded in restarting the ifup@eth0 service")
                logger.info("Well we succeded in restarting the ifup@eth0.service")
                pass								#Ok we succeeded in the restart were up and running.
            else:
                logger.info("We didn't succeed on the restart its still down")
                print("Well we didn't succeed on the restart of eth0 its still down")
                return(1)
        except:
           logger.info("We failed on the restart attempt of ifup@eth0.service")
           print("We failed on the restart attempt of ifupeth0.service")
           return(1)								#We errored out on the retry of starting the ifup@AP service

    else:
       print("ifup@eth0 service was running to begin with")
       logger.info("ifup@eth0 service was running to beging with")

    # If we are here then we have an ifup@eth0.service that is loaded active and/or we fixed it.

    logger.info("Starting CI services")
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
            logger.info("OK we don't have an ifup@CI.service")
            try:
                print("Well were going to try restarting the ifup@CI.service")
                logger.info("Well were going to try restarting the ifup@CI.service")
                os.system("/bin/systemctl restart ifup@"+CI)
                process = Popen(["/bin/systemctl","status","ifup@"+CI], shell=False, stdout=PIPE, stderr=PIPE)
                stdout, stderr = process.communicate()
                serva = str(stdout)
                x = serva.find("Active: active")
                print("looking for active active have: "+str(x))
                if x > 0:
                    print("Ok we succeeded in the restarting of the ifup@CI.service")
                    logger.info("OK we succeded in the restarting of the ifup@CI.service")
            except:
                logger.info("We failed on the retry of the ifup@CI.service")
                print("We failed on the retry of the ifup@CI.service restart")
                return(1)							#We errored out on the retry of starting the ifup@CI service
        else:
            logger.info("The ifup@CI.service is running fine so nothing to do")
            print("The ifup@CI.service is running finel so nothiing to do")
    else:
        print("No CI on this device or Ci has no passwords and ssid so we skip")
        logger.info("No CI on this device ")

    print("OK were done with all our testing the services should be googd at this point")
    return(0)										#End of sequence testing were done all is well



def check_PM2():
    """
    Ensure the PM2 Node.js process manager is running and restart it if not.

    PM2 manages the ConnectBox web application (the captive-portal UI served to
    connected clients).  If PM2 goes down -- which can happen after a crash or
    OOM event -- clients see a blank or error page instead of the content library.

    This function polls ``pm2 status`` in a tight loop until "online" appears in
    the output, restarting PM2 on each failed check.  A 5-second sleep between
    attempts gives PM2 time to fully initialise before the next status check.

    Why a blocking loop rather than a single attempt:
        PM2 is critical for the user-facing experience.  A single restart attempt
        that appears to succeed but leaves PM2 in a non-online state would cause
        client-facing failures for the entire next 20-iteration window (60 seconds)
        before the next scheduled check_PM2() call.  The loop guarantees that when
        this function returns, PM2 is confirmed online.

    Returns:
        int: The character position of "online" in the final ``pm2 status`` output
             (always >= 0, since the loop only exits when "online" is found).
    """
####### Utility to check if PM2 is operationa and restart if not

    x = -1
    while x < 0:
        process = Popen(["/usr/bin/pm2", "status"], shell=False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        x = str(stdout).find("online")
        if x < 0:
            logger.info("PM2 is not running we will restart")
            print("Restarting PM2 since its not running")
            process = os.popen("pm2 restart all")
            process.close()
            time.sleep(5)
        else:
            print("PM2 is already running")
    print("PM2 running as it should")
    x = (str(stdout).find("online"))
    return(x)


def sync_brand():
  """
  Detect changes to brand.j2 by comparing its current mtime to the last-seen mtime.

  brand.j2 is the ConnectBox configuration file (JSON) that controls the SSID name,
  logo, OLED display layout, feature flags (usb0NoMount, Enable_MassStorage, etc.),
  and server sync settings.  The admin web UI can update brand.j2 at any time while
  the daemon is running.

  This function uses the global ``otime_j2`` to track the last modification time
  seen.  On each call:
      - If os.path.getmtime() fails (file missing), return immediately without
        updating ``otime_j2``.
      - If the mtime has changed since the last call, update ``otime_j2`` and log
        that a change was detected.  The caller is responsible for acting on the
        change (e.g. re-reading Brand, updating the OLED display).
      - If the mtime is unchanged, log "no change to brand" and return.

  Note: In the current codebase the main loop re-reads brand.j2 on every iteration
  unconditionally, so sync_brand() serves primarily as a diagnostic/logging hook and
  a hook point for future change-triggered actions.

  Globals used:
      otime_j2 (float): Module-level variable holding the mtime of brand.j2 as of
                        the last call.  Initialised to 0 at startup so the first
                        call always detects a "change".

  Returns:
      int: 0 always (after normal execution); returns None implicitly if the file
           does not exist and the early-return path is taken.
  """
  file_j2  = "/usr/local/connectbox/brand.j2"
  global otime_j2

  try:
    time_j2 = os.path.getmtime(file_j2)
  except:
    return

  if otime_j2 != time_j2:
    otime_j2 = time_j2
    print("brand.j2 changed")
  else:
    print("no change to brand")
  return(0)


if __name__ == "__main__":

# First handle the partition expansion
# Determine if we are on NEO or CM
    brand_file = '/usr/local/connectbox/brand.j2'
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


    # Brand time testing
    global otime_j2
    otime_j2 = 0

    handler = logging.handlers.WatchedFileHandler( os.environ.get("LOGFILE", "/var/log/PxUSSBm.log"))
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    handler.setFormatter(formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(os.environ.get("LOGLEVEL", "INFO"))
    logger.addHandler(handler)

    print(sys.argv[0])
    try:
        if sys.argv[1] != "":
            delay = int(sys.argv[1])
        else:
            delay = 30
    except:
        delay = 30

    # Debug printing (to the journal): off unless PXUSBM_DEBUG is set (1
    # networking, 2 mount summary, 3-4 mount detail).  It used to be fixed at
    # 4, which printed about 600 lines a minute and pushed everything else out
    # of the box's 50 MB RAM log within a couple of hours.
    try:
        DEBUG = int(os.environ.get("PXUSBM_DEBUG", "0"))
    except ValueError:
        DEBUG = 0
    SSID=""
    connectbox_scroll=False
    first_time=True
    stop_hostapd=False
    areadyconf= ""
    logger.info("Starting PxUSBm")
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

    # Clear the creating_menus.txt status file so the OLED display does not get
    # stuck on a stale "Indexing" message from a run that was killed.  The file
    # is in /tmp (this used to remove /usr/local/connectbox/creating_menus.txt,
    # where it never is).  PxUSBm is also restarted while the box is running
    # (cron TestPxUSBm.py), so only when no mmiLoader is running: a running
    # index writes this file and treats it as "a run is in progress".
    if os.path.exists("/tmp/creating_menus.txt") and \
            subprocess.run(["pgrep", "-f", "mmiLoader.py"], capture_output=True).returncode != 0:
        try:
            os.remove("/tmp/creating_menus.txt")
        except OSError:
            pass
    # Remove a "loading new content" page left by an indexing run that was
    # killed outright (power cut on a box whose /tmp survives reboots), so
    # visitors are not shown it for ever.  Only when no mmiLoader is running.
    if os.path.exists("/tmp/connectbox-indexing.html") and \
            subprocess.run(["pgrep", "-f", "mmiLoader.py"], capture_output=True).returncode != 0:
        try:
            os.remove("/tmp/connectbox-indexing.html")
        except OSError:
            pass
    logger.info("PxUSBm Starting revision is "+version)

    # Load brand.j2 configuration.  brand.j2 is the single source of truth for all
    # device-specific settings (SSID name, logo, OLED page layout, feature flags).
    # If the file is missing or malformed, a default Brand dict is constructed with
    # safe defaults and written back to disk so subsequent reads succeed.
    try:
        f = open(brand_file, mode="r", encoding='utf-8')
        Brand = json.loads(f.read())
        f.close()
    except:
        Brand = {
            'Brand': "Connectbox",
            'enhancedInterfaceLogo': "",
            'Image': 'connectbox_logo.png',
            'Font': 27,
            'pos_x': 6,
            'pos_y': 0,
            'Device_type': a,
            "usb0NoMount": 0,
            "lcd_pages_main": 1,
            "lcd_pages_info": 1,
            "lcd_pages_battery": 1,
            "lcd_pages_multi_bat": 0,
            "lcd_pages_memory": 1,
            "lcd_pages_stats_hour_one": 1,
            "lcd_pages_stats_hour_two": 1,
            "lcd_pages_stats_day_one": 1,
            "lcd_pages_stats_day_two": 1,
            "lcd_pages_stats_week_one": 1,
            "lcd_pages_stats_week_two": 1,
            "lcd_pages_stats_month_one": 1,
            "lcd_pages_stats_month_two": 1,
            "lcd_pages_network": 1,     # IP addresses page (2026-11-13)
            "lcd_pages_internet": 1,    # Internet data page, when in use (2026-11-13)
            "lcd_pages_admin": 0,
            "Enable_MassStorage": "",
            "g_device": "g_serial",
            "otg": 0,
            "server_url": "",
            "server_authorization": "",
            "server_sitename": "",
            "server_siteadmin_name": "",
            "server_siteadmin_email": "",
            "server_siteadmin_phone": "",
            "server_siteadmin_country": ""
        }
        write_brand_file(Brand)
        logger.info("Created new brand.j2 with defaults")

    NoMountUSB = Brand["usb0NoMount"] 			   # Note: brand is type dict, so no "find" method
    rpi_platform=False
    rm3_platform=False
    PI_stat = False
    OP_stat = False


# -- sort out the SSID
# If the hardware revision is known and the brand file records a different Device_type
# (e.g. after swapping an SD card between platforms), update brand.j2 to match the
# actual hardware.  This prevents using a partition layout or display config that was
# tuned for a different board.  Quotation marks are stripped from the SSID because
# json.dumps() sometimes wraps string values in extra quotes which would appear
# verbatim in the hostapd SSID field.
    if (version != "Unknown") and (version != "Error"):
      logger.info("Major type: "+a)
      if Brand["Device_type"].find(a)<=0:                    # Make sure the brand file is what we expect as were on this hardware.
        Brand["Device_type"] = '"'+a+'"'
        # Multi-battery page: on when the front panel's ATtiny battery
        #  controller answers (2026-11-06: this always set 0, so on every new
        #  CM4 card the first start turned off the page the build had turned
        #  on; Kirk: a Pi/CM4 with the ATtiny has it on by default).
        Brand["lcd_pages_multi_bat"] = 1 if attiny_present(a) else 0
        logger.info("Device_type set to " + a + ", multi-battery page " + str(Brand["lcd_pages_multi_bat"]))
        write_brand_file(Brand)
        os.sync()
        SSID = Brand["Brand"]
    else:
        SSID = "ABC"
    x=SSID.find('"')                          #Remove all the quotation marks around the  SSID
    while ( x >= 0 and len(SSID)>0):
      SSID = SSID.replace('"','')
      x=SSID.find('"')

    logger.info("SSID from file is now: "+SSID)

    # Set platform flags based on the Device_type string in brand.j2.
    # These flags control partition table layout (do_fdisk/do_resize2fs),
    # network interface naming assumptions, and OLED page counts.
    # The checks are intentionally sequential (not elif) so that a Device_type
    # string containing multiple keywords (e.g. from a corrupted file) sets the
    # last matching flags -- RM3 is last and thus takes highest priority.
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

    logger.info("device is RPI? "+str(rpi_platform)+" rm3_platform? "+str(rm3_platform)+" PI_stat? "+str(PI_stat)+" OP_stat? "+str(OP_stat))
    print("device is RPI? "+str(rpi_platform)+" rm3_platform? "+str(rm3_platform)+" PI_stat? "+str(PI_stat)+" OP_stat? "+str(OP_stat))

    # --- Partition expansion state machine ---
    # expand_progress.txt acts as a persistent state flag across reboots:
    #   Missing            -> first boot after imaging; run do_fdisk() then reboot
    #   "fdisk_done ..."   -> fdisk completed on previous boot; run do_resize2fs() then reboot
    #   "resize2fs_done"   -> expansion complete; fall through to normal operation
    #   "running"          -> daemon was already running (written at end of this block)
    # Both do_fdisk() and do_resize2fs() end with os.system('shutdown -r now') so
    # they never return.  Code after this block only executes when expansion is done.
    file_exists = os.path.exists(progress_file)
    if file_exists == False:
        logger.info("PxUSBm starting the fdisk operation for expansion")
        os.sync()
        do_fdisk(rpi_platform, rm3_platform)             # this ends in reboot() so won't return
    else:
        f = open(progress_file, "r")
        progress = f.read()
        f.close()
        if "fdisk_done" in progress:
            # Extract the max partition number saved by do_fdisk() so do_resize2fs()
            # knows which partition to expand (e.g. p2 on RPi, p1 on NEO).
            maxp = progress.split("maxp=")
            max_partition = maxp[1][0]
            logger.info("PxUSBm starting the resize2fs to format full disk")
            os.sync()
            do_resize2fs(rpi_platform, rm3_platform)     # this ends in reboot() so won't return

        else:
            logger.info("PxUSBm disk and format expansion already completed waiting for netfiles")
            print("PxUSBm disk and format expansion already completed waiting for netfiles")


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

    logger.info("Getting Ready for Network Names and Network Class")
    print("Getting ready for network names and neewtwork class\n")

    setNetworkNames()
    print("finished setNetworkNames")

    getNetworkClass(1)  					# Note: calls fixfiles() if required... the (1) signals minimal ifconfig down/up
    print("Finished get network class")

    # Ensure neo-battery-shutdown is running before entering the main loop.
    # This service monitors battery voltage and initiates a clean shutdown if the
    # battery falls below a safe threshold.  Without it, a flat battery causes an
    # unclean shutdown that can corrupt the SD card filesystem.
    # The loop retries every 5 seconds -- the service sometimes takes a moment to
    # appear active after a network reconfiguration restart cascade.
    print("Checking on neo-battery-shutdown")
    x = -1
    while x < 0:
        process = Popen(["/bin/systemctl","status","neo-battery-shutdown"], shell=False, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        x = str(stdout).find("Active: active (running)")
        if x < 0:
            logger.info("PxUSBm is restarting neo-battery-shutdown")
            print("PxUSBm is restarting neo-battery-shutdwon")
            process = os.popen("systemctl restart neo-battery-shutdown")
            process.close()
            time.sleep(5)
    print("neo-battery-shutdown is running")

    check_PM2()

    logger.info("PxUSBm moving to run mode")
    f = open(progress_file, "w")
    f.write("running")
    f.close()
    os.sync()
    print("PxUSBm moving to run mode")


    x = 95    # give time for network to come up before trying to fix it

    logger.info("PAUSING PXUSBM.PY FOR THE FOLLLOWING SECONDS "+str(delay))
    print("PUAUSING PXUSBM.PY FOR THE FOLLOWING SECONDS "+str(delay))
    time.sleep(delay)			#Sleep for 1 min to let the interfaces come up
    logger.info("DELAY COMPLETE STARTING CHECKING OF SERVICES!!")
    print("DELAY COMPLETE STARTING CHECKING OF SERVICES!!")

    if not (checkServices()): 			#This calls a check service routine that verifies that networking , ifup, ifdown came up and are running, otherwise
        time.sleep(5)				#it attemtps to fix them, but we only try twice then go on.
        checkServices()                         #we wait between attempts.

    # --- Main daemon loop ---
    # `while (x == x)` is an intentional infinite loop (x always equals itself).
    # x is a counter used to schedule periodic tasks at different rates:
    #   every iteration (~3 s): re-read brand.j2, run mountCheck()
    #   every 10 iterations (~30 s): check AP mode, eth0, CI link state and internet sharing
    #   every 20 iterations (~60 s): check wpa_supplicant country code, remembered Wi-Fi networks, check PM2
    # x is reset to 0 when it exceeds 1,000,000,000,000 to prevent integer overflow
    # over extremely long uptimes.
    logger.info("Getting ready to start Mount Checks")
    release_usb_slots()
    while (x == x):                         # main loop that we live in for life of running

          # Re-read brand.j2 on every iteration so that admin changes (SSID, feature
          # flags, usb0NoMount) take effect without restarting the daemon.
          try:
              f = open(brand_file, mode="r", encoding='utf-8')
              Brand = json.loads( f.read() )
              f.close()
              NoMountUSB = Brand["usb0NoMount"]    # Note: brand is type dict, so no "find" method
          except:
              pass

          # USB mount check -- every iteration.
          # Skipped entirely when usb0NoMount is set in brand.j2 (e.g. during
          # mass-storage / OTG mode where the USB port is used for something else).
          # dbCheck() is only called on Connectbox Scroll hardware (connectbox_scroll=True)
          # because that variant uses a MySQL database for content serving.
          if (int(NoMountUSB) <= 0):
             if DEBUG > 3: print("PxUSBm Going to start the mount Check")
             logger.debug("Doing a mount check "+str(x) + " time is " +time.asctime())
             if x % 200 == 0:                  # about every 10 minutes: a sign of life in the log
                 logger.info("PxUSBm running, mount check " + str(x) + " time is " + time.asctime())
             mountCheck()                   # Do a usb check to see if we have any inserted or removed.
             check_internal_content()       # No key at usb0: show the box's own content
             if connectbox_scroll: dbCheck()
          elif x % 200 == 0:                # suspended (e.g. during a front-panel copy): note it now and then
              logger.info("Mount checks are suspended by usb0NoMount in brand.j2, check " + str(x) + " time is " + time.asctime())



          if ((x % 10)==0):
            # AP health check -- every ~30 seconds.
            # Verify the AP wlan is still in Mode:Master.  If it has dropped (can
            # happen after a kernel driver reset or power spike), attempt recovery in
            # escalating steps: hostapd restart -> ifdown/ifup -> full getNetworkClass().
            AP = get_AP()
            AP_up = check_iwconfig(AP)  # returns 1 if up
            logger.debug("checking AP is up "+str(x)+ " time is "+time.asctime())
            if (not AP_up):
              logger.info("AP was not up and didn't  show correctly")
              # A hostapd restart first (2026-11-05): the usual failure on the
              # CM4 (8812au) is hostapd ENABLED with a dead radio, which one
              # restart fixes; ifdown/ifup also reruns wifi_configurator
              # (new scan, new channel) and restarts hostapd twice more.
              restart_hostapd()
              time.sleep(3)
              if not(check_iwconfig(AP)):
                  try:
                      os.system("ifdown wlan"+str(AP))
                  except:
                      pass
                  try:
                      os.system("ifup wlan"+str(AP))
                  except:
                      pass
                  if not(check_iwconfig(AP)):
                     logging.info("Still not up so having to resort to getNetworkClass")
                     getNetworkClass(1)       # try to fix the problem (shouldn't get here normally)

            logger.debug("checking  eth0 " +str(x)+ " time is "+time.asctime())
            check_eth0()      # make sure eth0 is up

            logger.debug("checkinng Client IF " + str(x) + " time is "+time.asctime())
            CI = get_CI()
            check_stat_CI(CI)

            # Internet sharing for phones on the ConnectBox Wi-Fi (admin
            # page Advanced switch, brand.j2 internet_sharing) -- see
            # check_internet_sharing.
            check_internet_sharing()

          if ((x % 20)==0):
            logger.debug("PxUSBm Going to do a Network check " + str(x) + " time stamp " + time.asctime())

            # wpa_supplicant country code fix -- every ~60 seconds.
            # Some builds ship with an empty country= line in wpa_supplicant.conf.
            # An empty country code prevents wpa_supplicant from connecting to 5 GHz
            # networks in many regulatory domains.  We default to "US" if the field
            # is blank.  This is a safe fallback -- the admin can set the correct
            # country via the web UI which writes a proper value that won't match
            # 'country=\n' and therefore won't be overwritten.
            wpa_File = '/etc/wpa_supplicant/wpa_supplicant.conf'
            f = open(wpa_File, mode="r", encoding='utf-8')
            filedata=f.read()
            f.close()
            if 'country=\n' in filedata:
                filedata = filedata.replace('country=\n', 'country=US\n')
                with open(wpa_File, 'w') as f:
                  f.write(filedata)
                f.close()

            # Remembered client Wi-Fi networks -- every ~60 seconds (see
            # check_known_wifi): learn the connected network once the internet
            # works through it, and keep the remembered ones in wpa_supplicant.conf.
            try:
                check_known_wifi(get_CI())
            except Exception as e:
                logger.info("Remembered Wi-Fi check failed: " + str(e))

          # PM2 health check -- every ~60 seconds.
          # PM2 manages the Node.js web application.  Check separately from the
          # network block above so it runs even if the x%20 network block is skipped
          # due to a future refactor -- PM2 being down is independently critical.
          if ((x % 20)==0):
              logger.debug("Checking PM2 status " + str(x) + " time is " + time.asctime())
              check_PM2()

          # Increment loop counter; wrap at 1 trillion to prevent overflow on
          # devices that run for years without a reboot.
          x += 1
          if x > 1000000000000: x = 0
          time.sleep(3)
# end of  while loop here

