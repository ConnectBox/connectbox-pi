# ConnectBox System Scripts

> **Status (2026-10-05):** `PxUSBm.py` is the official owner of USB mounting (and starting
> `mmiLoader.py`) and of network recovery. This folder originally held event-driven
> replacements for those jobs; they were retired because they ran *alongside* PxUSBm and
> raced it, and are no longer in the repo:
>
> - `usb_mounter.py` + `99-usb-automount.rules` (udev USB mounting)
> - `network-watchdog.py` + `network-watchdog.service` (WiFi/AP recovery)
>
> Ansible removes both from devices where they were installed. Do not reinstall them.
>
> Still here: `first-boot-expand.py`, which overlaps PxUSBm's own first-boot partition
> expansion. Whether to keep it is undecided.

## first-boot-expand

One-shot partition expansion on the first boot of a new image, run by
`first-boot-expand.service`. It is skipped once `/usr/local/connectbox/expand_progress.txt`
exists (the same progress file PxUSBm uses).

```bash
sudo cp first-boot-expand.py /usr/local/connectbox/bin/
sudo chmod +x /usr/local/connectbox/bin/first-boot-expand.py
sudo cp first-boot-expand.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable first-boot-expand.service
```

## Native service restarts

These systemd overrides make `hostapd` and `neo-battery-shutdown` restart themselves if
they fail. They are independent of the scripts above.

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
