# ConnectBox Modular System Scripts

> **Status (2026-10-05):** `PxUSBm.py` is the official USB mounter. Ansible no longer installs
> `usb_mounter.py` or `99-usb-automount.rules`, and removes them from provisioned devices,
> because udev and PxUSBm both mounting every inserted USB raced each other. PxUSBm now also
> starts `mmiLoader.py`. The USB part of this kit is kept for reference only — do not install
> it alongside PxUSBm.

This directory contains the modernized, event-driven replacements for `PxUSBm.py`. By breaking apart the monolithic script, we achieve lower CPU usage, higher stability, and faster USB mounting.

## 1. File Placements

Move the scripts to the ConnectBox binary directory:
```bash
sudo cp *.py /usr/local/connectbox/bin/
sudo chmod +x /usr/local/connectbox/bin/first-boot-expand.py
sudo chmod +x /usr/local/connectbox/bin/network-watchdog.py
sudo chmod +x /usr/local/connectbox/bin/usb_mounter.py
```

Move the `udev` rule to handle USB automounting:
```bash
sudo cp 99-usb-automount.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

Move the `systemd` services to `/etc/systemd/system/`:
```bash
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## 2. Enabling Native Service Restarts

Instead of relying on Python to monitor daemon crashes, we configure `systemd` to automatically restart services if they fail.

Run the following commands to add `Restart=always` to the existing services:

### For `hostapd`:
```bash
sudo mkdir -p /etc/systemd/system/hostapd.service.d/
echo -e "[Service]\nRestart=always\nRestartSec=5" | sudo tee /etc/systemd/system/hostapd.service.d/override.conf
```

### For `neo-battery-shutdown`:
```bash
sudo mkdir -p /etc/systemd/system/neo-battery-shutdown.service.d/
echo -e "[Service]\nRestart=always\nRestartSec=5" | sudo tee /etc/systemd/system/neo-battery-shutdown.service.d/override.conf
```

Reload `systemd` to apply these overrides:
```bash
sudo systemctl daemon-reload
```

## 3. Disabling PxUSBm.py

Ensure the old script is disabled. If it was launched from `/etc/rc.local`, edit `/etc/rc.local` and remove or comment out the line calling `PxUSBm.py`.

## 4. Enabling the New Services

```bash
sudo systemctl enable first-boot-expand.service
sudo systemctl enable network-watchdog.service

sudo systemctl start network-watchdog.service
```
