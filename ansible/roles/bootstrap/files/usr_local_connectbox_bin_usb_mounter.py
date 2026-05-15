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

    # udev already mounts via fstab or direct rule usually, 
    # but we can ensure it's mounted here if we want or just let udev do it.
    # In the refactor, we let the udev rule do the actual `mount` command first, 
    # and then it calls this script to handle the post-mount actions.
    
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
    print(f"Device {dev_node} removed.")
    # Stop the content loader if it is still running — sends SIGTERM so mmiLoader
    # can exit cleanly rather than continuing to attempt IO on the unmounted path.
    os.system("systemctl stop connectbox-loader.service 2>/dev/null")

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
