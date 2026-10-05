# ConnectBox Master Changes Log

This file tracks the architecture changes, thinking process, and code refactors made to the ConnectBox system.

## 1. PxUSBm.py Refactor & Modularization (Completed)
**Goal:** Deconstruct the monolithic `PxUSBm.py` script into single-responsibility, event-driven scripts.
**Changes Made:**
* Created `first-boot-expand.py` to handle initial filesystem expansion, triggered by a one-shot `systemd` service (`first-boot-expand.service`).
* Created `usb_mounter.py` triggered natively by `udev` rules (`99-usb-automount.rules`) to handle USB insertion events instead of using a constant polling loop.
  * **Reversed 2026-10-05:** `PxUSBm.py` is the official mounter again. It now also starts `mmiLoader.py`, and handles Linux file systems (ext4 etc.) and drives with no partition table. Ansible removes `usb_mounter.py` and the udev rule from devices, since udev and PxUSBm were both mounting every USB.
* Created `network-watchdog.py` as a lightweight daemon to handle Wi-Fi recovery (unloading/loading kernel drivers dynamically via `rmmod`/`modprobe`) and restarting `hostapd`.
* Relied on `systemd` `Restart=always` overrides for process management instead of Python-based checks.

## 2. Deprecation of `brand.txt` (Completed)
**Goal:** Eliminate dual-source-of-truth syncing between `brand.txt` and `brand.j2`. Move all remaining system components to read directly from the JSON-based `brand.j2` file.
**Changes Made:**
1. Updated `globals.py` to exclusively read and load configuration from `/usr/local/connectbox/brand.j2` instead of `brand.txt`.
2. Cleaned up obsolete synchronization code in `globals.py`, completely removing any reads or writes to `/usr/local/connectbox/brand.txt`.
3. Updated `BrandCreationTool.py` to output configurations directly to `brand.j2`.
4. Modified `buttons.py`, `usb.py`, `hats.py`, and `mmiLoader.py` to correctly reflect the updated `brand.j2` references, eliminating confusing/outdated comments referencing `brand.txt`.
5. Removed the `sync_brand()` logic entirely from `network-watchdog.py`.
6. Moving forward, the source of truth for device branding and specific flag configurations like `usb0NoMount` will exclusively be `brand.j2`.
