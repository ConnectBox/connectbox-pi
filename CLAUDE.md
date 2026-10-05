# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

ConnectBox/TheWell is an offline media-sharing appliance for Raspberry Pi and similar SBCs (NanoPi NEO, Orange Pi Zero 2, Radxa CM3). It creates a WiFi access point with a captive portal, serves media from a USB drive via an enhanced web interface, and optionally includes Moodle LMS. The entire system is provisioned via Ansible onto a target device running Raspbian/Debian.

## Provisioning

```bash
# Install Python/Ansible dependencies
pip install -r requirements.txt

# Provision a connected device
ansible-playbook -i <device_ip>, ansible/site.yml

# Ansible lint (CI check)
ansible-lint ansible/site.yml
```

The Vagrant file provides three local VMs (stretch, focal, ubuntu) for development without real hardware — `vagrant up focal` provisions via Ansible automatically.

## Architecture

### Playbook structure

`ansible/site.yml` is the entry point. It detects hardware type from `/sys/firmware/devicetree/base/model` (Raspberry Pi, CM4, OrangePi Zero2, NEO, Radxa CM3) then invokes the `connectbox-pi` role. That role's `meta/main.yml` declares ~15 role dependencies that run in order:

**Key roles:**

| Role | What it deploys |
|------|----------------|
| `bootstrap` | Core system files — `mmiLoader.py`, `PxUSBm.py`, `ConnectBoxManage.sh`, `shutdown.sh`, `brand.j2`, SSH keys, poweroff binary, logrotate config |
| `hat-service` | OLED display driver and `neo-batterylevelshutdown` service for battery monitoring, button handling, and shutdown |
| `dns-dhcp` | dnsmasq for DNS/DHCP on the WiFi interface |
| `wifi-ap` | hostapd WiFi access point |
| `enhanced-content` | Downloads and installs the enhanced media interface (mediainterface + connectbox-admin-ui) from GitHub releases, installs ffmpeg |
| `nginx` | Five vhosts: captive portal, classic UI, enhanced UI, static site, icon-only |
| `captive-portal` | Flask captive portal (Python venv at `/var/www/connectbox/captiveportal_venv`) |
| `webserver-content` | Clones `connectbox-client` repo, installs Flask/gunicorn for chat and admin APIs |
| `usb-content` | udev rules at `ansible/roles/usb-content/files/99-usb-automount.rules` (identical copy in `system_scripts/`) — mounts USB to `/media/usb0`, calls `usb_mounter.py` |

### Source file naming convention

Files in `ansible/roles/bootstrap/files/` use underscores to encode their deploy path. `usr_local_connectbox_bin_mmiLoader.py` deploys to `/usr/local/connectbox/bin/mmiLoader.py`. Edit the repo file, then `scp` to device for testing before committing.

### Comment Policy

all functions should have comprehensive comments explaining what the function does

Each major loop or section in a file should have a comment explaining what it does, what the logic is and why it is done this way


### Brand configuration

Device configuration is stored as JSON in `/usr/local/connectbox/brand.j2`. This is the single source of truth — `brand.txt` has been eliminated. `ConnectBoxManage.sh` uses `jq` to read/write it. The Node.js backend (`/var/www/enhanced/connectbox-manage/src/`) also reads it directly.

### USB content pipeline

1. USB inserted → udev ADD event → `usb_mounter.py` → launches `mmiLoader.py` in background. The udev rule matches partitions (`sda1`) and also whole disks that carry a file system with no partition table (`mkfs.ext4 /dev/sdb`).
   - On file systems with Unix permissions (ext2/3/4, xfs, btrfs, f2fs) `mmiLoader.py` first runs `make_usb_world_readable()` — the equivalent of `chmod -R a+rX` that skips symlinks and only touches entries missing bits — so nginx (`www-data`) can read files written by another computer's user account. FAT/exFAT/NTFS are left alone.
2. `mmiLoader.py` checks for `saved.zip` on the USB:
   - **Found + same mtime**: fast unzip into `/var/www/enhanced/content/www/assets/content/`
   - **Found + different mtime or missing**: full index walk — scans files, extracts thumbnails via ffmpeg, generates JSON, writes `saved.zip` at the end
3. Thumbnails stored as hidden files on USB (`.thumbnail-<lang>-<slug>.png`) to avoid re-extraction
4. `saved.zip` mtime marker written to `/tmp/.saved_zip_mtime` to detect USB swap

Force a full re-index by deleting `saved.zip` from the USB.

### Admin and stats backend

Port 5002: Node.js (`/var/www/enhanced/connectbox-manage/src/index.js`) managed by PM2. This is the `connectboxmanage` CLI target — all `get`/`set` calls go through HTTP to this process. If port 5002 is down, `connectboxmanage` throws a traceback instead of JSON.

Port 5000: Python gunicorn serving `python/main.py` (chat + admin API Flask app).

Port 5001: Python captive portal.

### Shutdown service

`neo-battery-shutdown.service` runs `/usr/local/connectbox/battery_tool_venv/bin/neo_batterylevelshutdown`. Left button held ≥4 s → `shutdownDevice()` → `/usr/local/bin/poweroff/poweroff` (symlink to `shutdownShell.sh`) → `shutdown.sh` (Python: sets AXP209 register 0x32 bit 7 via i2c, then calls `/sbin/shutdown -h now`). The i2c bus is 0 for NEO, 10 for CM4.

## Device access

SSH config at `~/.ssh/config` has wildcard for `192.168.1.*` using `root` + `id_ed25519`. Direct SSH: `ssh root@<device_ip>`. Build Pi: `ssh build`.

Deploying a single file for testing:
```bash
scp ansible/roles/bootstrap/files/usr_local_connectbox_bin_mmiLoader.py root@<ip>:/usr/local/connectbox/bin/mmiLoader.py
```

## Git workflow

Work on `master`. Remotes: `origin` = ConnectBox/connectbox-pi (org), `fork` = kirkdwilson/connectbox-pi. After each commit push to both: `git push origin master && git push fork master`. Use conventional messages, e.g. `fix(usb-mounter): ...`.

The copy at `Documents\Hobby - ConnectBox\Antigravity\connectbox-pi` is stale — work only in this repo.

## Related repos

Sibling checkouts in `C:\Users\kirkw\Documents\Github\`: `connectbox-mediainterface` (Angular/Ionic front end served as the enhanced UI), `connectbox-admin-ui`, `connectbox-manage` (Node.js port-5002 backend), `connectbox-hat-service` (OLED/battery/buttons), `connectbox-chathost`, `connectbox-reports`, `connectbox-access-log-analyzer`, `simple-offline-captive-portal` (Flask captive portal), `armbian-build`.

## Patched mediainterface JS

The `enhanced-content` role patches compiled mediainterface bundles on the device with shell tasks in `ansible/roles/enhanced-content/tasks/main.yml`:
- `6.js` `goToDetails` — HTML items open via `window.location.href` instead of the detail page. Because that skips the detail page (where the stock app reports views), the patch sends the view report itself (`PUT /admin/api/weblog`, same body as `StatReporterProvider`, honours `disable_stats`). The function is replaced by brace matching, so it upgrades older patched copies too.
- `3.js` `MediaDetailPage.prototype.loadData` — on a language change, `popToRoot()` before `setLanguage()` (prevents "media missing!" and blank pages)

The `3.js` patch matches an exact compiled string with `ignore_errors: yes`, so it silently no-ops if a new mediainterface release changes the code. Inside these `shell: |` blocks YAML strips the block's indentation, so string literals end up less indented than the compiled JS (which uses 4/8 spaces) — test a patch against the real release `6.js`/`3.js` before relying on it. Recheck them after any mediainterface upgrade.

## Tests

`ansible/roles/bootstrap/files/test_mmiLoader.py` covers the mmiLoader helper functions (loads the file via `importlib.util.spec_from_file_location`; kept Python 3.7 compatible with `contextlib.ExitStack`). Run it after any mmiLoader change.

## Important invariants

- **Captive portal must support very old phones**: devices are deployed in disadvantaged countries with iOS 9 / Android 4–5 era phones. The old-OS checks in `captiveportal/views.py` (sibling repo `simple-offline-captive-portal`) are intentional — do not remove or "modernize" them.
- **Video must be H.264 in MP4**: browsers don't play MPEG-4 Part 2 (`mp4v`). `content["mimeType"]` must be the real MIME type (`video/mp4`), not the media type (`video`).

- **Line endings**: All `.sh` and `.py` files must have Unix LF endings. `.gitattributes` enforces this. CRLF causes `#!/bin/bash^M: bad interpreter` on the device. Check with `cat -A <file> | head -1` — should show `$` not `^M$`.
- **brand.j2 is JSON**: Any script that writes to `brand.j2` must produce valid JSON. `node -e "JSON.parse(require('fs').readFileSync('/usr/local/connectbox/brand.j2'))"` to verify.
- **mmiLoader single-instance guard** uses `/proc/*/cmdline` inspection (not `pgrep -f`) to avoid false positives from the parent shell process.
- **saved.zip is written last**: `mmiLoader.py` checks `os.path.ismount("/media/usb0")` at each directory iteration and before writing `saved.zip`. If USB disconnects mid-run it exits cleanly without corrupting the content directory.
