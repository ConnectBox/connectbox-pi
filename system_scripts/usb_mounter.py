#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import time

def read_brand():
    try:
        f = open("/usr/local/connectbox/brand.j2", "r", encoding='utf-8')
        brand = json.loads(f.read())
        f.close()
        return brand
    except:
        return {"Brand": "ConnectBox", "usb0NoMount": 0}

def handle_add(dev_node):
    brand = read_brand()
    if brand.get("usb0NoMount", 0) != 0:
        print("Mounting disabled by brand configuration.")
        return

    mount_point = "/media/usb0"
    if not os.path.exists(mount_point):
        os.makedirs(mount_point)

    # Clean up any stale/stacked mounts from previous USB inserts so the new
    # device gets a clean mount point.  Without this, each USB swap stacks a new
    # bind on top of the old one because `umount /dev/sdX` fails once the device
    # node is physically gone (it no longer exists to match).
    for _ in range(10):
        if os.system("grep -qs ' /media/usb0 ' /proc/mounts") != 0:
            break
        os.system("umount -l /media/usb0 2>/dev/null")

    # Mount the new device.  Try utf8 first (VFAT/exFAT); fall back without it
    # for ext4 and other filesystems that don't accept the utf8 option.
    ret = os.system("/bin/mount -o noexec,nodev,noatime,nodiratime,utf8 " + dev_node + " " + mount_point)
    if ret != 0:
        ret = os.system("/bin/mount -o noexec,nodev,noatime,nodiratime " + dev_node + " " + mount_point)
    if ret != 0:
        print("Failed to mount " + dev_node + " to " + mount_point)
        return

    # Wait a second to ensure mount is complete
    time.sleep(1)

    print("Executing post-mount hooks for ConnectBox...")

    # 1. SSH Enabler
    os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/enable-ssh && (/bin/systemctl is-active ssh.service || /bin/systemctl enable ssh.service && /bin/systemctl start ssh.service)'")

    # 2. Enhanced Content Load (mmiLoader)
    try:
        os.system("rm /usr/local/connectbox/complex_dir 2>/dev/null")
    except:
        pass
    # Reset any previous run of the transient unit so systemd-run can reuse the name.
    # Without this, --remain-after-exit keeps the unit alive after exit and the second
    # USB insert fails silently because the unit name already exists.
    os.system("systemctl stop connectbox-loader.service 2>/dev/null; systemctl reset-failed connectbox-loader.service 2>/dev/null")
    os.system("/usr/bin/systemd-run --unit=connectbox-loader --description='ConnectBox Content Loader' --remain-after-exit /usr/bin/python3 /usr/local/connectbox/bin/mmiLoader.py")

    # 3. Upgrade Enabler
    if os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/.connectbox/upgrade/upgrade.py'") == 0:
        os.system("python3 /media/usb0/.connectbox/upgrade/upgrade.py")

    # 4. Moodle Course Loader (TheWell)
    if brand.get("Brand") == 'TheWell':
        os.system("/bin/sh -c '/usr/bin/test -f /media/usb0/*.mbz && /usr/bin/php /var/www/moodle/admin/cli/restore_courses_directory.php /media/usb0/' >/tmp/restore_courses_directory.log 2>&1 &")

def handle_remove(dev_node):
    print("Device " + dev_node + " removed.")
    # Stop the content loader if it is still running
    os.system("systemctl stop connectbox-loader.service 2>/dev/null")
    # Lazy unmount: -l detaches the mount point immediately even if the device
    # node is already physically gone (avoids stale mount entries on the next insert).
    if os.system("umount -l " + dev_node + " 2>/dev/null") != 0:
        # Device node no longer exists; unmount by mount point instead
        os.system("umount -l /media/usb0 2>/dev/null")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: usb_mounter.py [add|remove] [dev_node]")
        sys.exit(1)

    action = sys.argv[1]
    dev_node = sys.argv[2]

    if action == "add":
        handle_add(dev_node)
    elif action == "remove":
        handle_remove(dev_node)
