# ConnectBox System Scripts

> **Status (2026-10-05):** `PxUSBm.py` is the official owner of:
>
> - USB mounting, and starting `mmiLoader.py` to index the USB
> - network recovery (AP / client interface checks, `hostapd` restarts)
> - first-boot partition expansion (`/usr/local/connectbox/expand_progress.txt`)
>
> This folder originally held event-driven replacements for those jobs. They were
> retired because they ran *alongside* PxUSBm and raced it, and are no longer in the repo:
>
> - `usb_mounter.py` + `99-usb-automount.rules` (udev USB mounting)
> - `network-watchdog.py` + `network-watchdog.service` (WiFi/AP recovery)
> - `first-boot-expand.py` + `first-boot-expand.service` (partition expansion)
>
> Ansible removes all of them from devices where they were installed. Do not reinstall them;
> change PxUSBm instead. They remain in git history.

## Native service restarts

These systemd overrides make `hostapd` and `neo-battery-shutdown` restart themselves if
they crash. They only restart a crashed process, so they do not compete with PxUSBm.

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
