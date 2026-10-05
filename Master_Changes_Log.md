# ConnectBox Master Changes Log

This file tracks the architecture changes, thinking process, and code refactors made to the ConnectBox system.

## 1. PxUSBm.py Refactor & Modularization (Completed)
**Goal:** Deconstruct the monolithic `PxUSBm.py` script into single-responsibility, event-driven scripts.
**Changes Made:**
* Created `first-boot-expand.py` to handle initial filesystem expansion, triggered by a one-shot `systemd` service (`first-boot-expand.service`).
  * **Reversed 2026-10-05:** `PxUSBm.py` already does first-boot partition expansion (same `expand_progress.txt`). `first-boot-expand` was removed from the repo and Ansible removes it from devices.
* Created `usb_mounter.py` triggered natively by `udev` rules (`99-usb-automount.rules`) to handle USB insertion events instead of using a constant polling loop.
  * **Reversed 2026-10-05:** `PxUSBm.py` is the official mounter again. It now also starts `mmiLoader.py`, and handles Linux file systems (ext4 etc.) and drives with no partition table. Ansible removes `usb_mounter.py` and the udev rule from devices, since udev and PxUSBm were both mounting every USB. The files were removed from `system_scripts/` too.
* Created `network-watchdog.py` as a lightweight daemon to handle Wi-Fi recovery (unloading/loading kernel drivers dynamically via `rmmod`/`modprobe`) and restarting `hostapd`.
  * **Reversed 2026-10-05:** `PxUSBm.py` owns network recovery. `network-watchdog` ran alongside it (both doing `ifdown`/`ifup`, driver reloads and `hostapd` restarts); it was removed from the repo and Ansible removes it from devices.
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

## 3. USB, languages and performance (2026-10-05)
**Goal:** Make Linux-formatted USBs, non-English USBs and the web interface work reliably on the NanoPi NEO test unit.
**Changes Made:**
* **One owner per job.** `PxUSBm.py` is the only USB mounter and starts `mmiLoader.py` itself (transient unit `connectbox-loader`); it also owns network recovery and first-boot partition expansion. The parallel `usb_mounter.py`/udev rule, `network-watchdog` and `first-boot-expand` were retired (see section 1). `mmiLoader.py` is the only writer of `interface.json` (`apply_translations.py`, hand-installed on the test unit, was merged in and retired).
* **Linux file systems.** PxUSBm mounts ext2/3/4, xfs, btrfs and f2fs without the FAT-only `utf8` option and skips `dosfsck`, and mounts whole-disk sticks with no partition table. mmiLoader makes Linux-formatted content world-readable before indexing (nginx got 403 otherwise).
* **Bug fixes found on the device:** `systemctl stop --wait` is invalid on systemd 247, so re-indexing after the first USB insert since boot had silently failed since May; a failed mount was recorded as mounted (`res >= 0`) and an empty mount point was indexed.
* **Interface translations and right-to-left.** Each language's `interface.json` comes from `/usr/local/connectbox/translations/<code>.json` (reviewed fa/ar/es/pt/zh-CN shipped; other languages looked up online with MyMemory and saved; English offline). RTL languages get `"rtl": true`. `saved.zip` restores refresh both. App patches (`ansible/roles/enhanced-content/files/patch_*.py`): language button shows the language name, footer Configuration link and chat page translated, chat right-to-left, returning visitors pick up `rtl`.
* **Usage stats.** Opening web (HTML) content is counted again: the `6.js` patch that opens it directly now sends the view report the detail page used to send. The earlier patch had never applied on stock installs (YAML indentation).
* **Web content links.** Broken links inside web content redirect to that item's start page instead of a blank page (nginx).
* **Speed.** nginx gzip for CSS/JS/JSON: the 4.9 MB app bundle is sent as 1.0 MB (first load ~44 s -> ~7 s over WiFi).
* **Home button.** nginx adds a floating house button (back to the ConnectBox menu) to every web-content and ZIM page as it is served (`libnginx-mod-http-subs-filter`; the `nginx.conf` template now loads Debian's dynamic modules).
* **ZIM files (offline websites).** New Ansible role `kiwix` (kiwix-serve 3.8.2, per-board build, `--monitorLibrary`); nginx `location ^~ /kiwix/`; mmiLoader rebuilds the Kiwix library on every USB insert and makes a stand-alone web-content card per ZIM (title, description, icon from the ZIM; multi-language ZIMs cross-listed); PxUSBm empties the library on removal; no download button for ZIM cards. Tested on the NanoPi NEO with 79 MB-2.1 GB ZIMs (articles ~0.08 s, search ~1 s, ~60 MB RAM).
* **ZIM card icons.** Pure-Python PNG check: dark icons on transparent backgrounds are flattened onto white, empty icons fall back to the standard web icon.
* **One IP per box.** `dhcpcd` was also running DHCP on the WiFi client interface because `denyinterfaces` sat inside an `interface` block; moved to global scope.
