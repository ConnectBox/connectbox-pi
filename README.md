[![Build Status](https://travis-ci.org/ConnectBox/connectbox-pi.svg?branch=master)](https://travis-ci.org/ConnectBox/connectbox-pi)

# This version of ConnectBox

TheWell is a old variant of ConnectBox that adds Moodle Learning Management System (v. 3.9.3), PHP (v. 7.4) and MySQL (MariaDB) (vv 10.3) to bring training system and learning content to the ConnectBox platform.

Summary Of Changes:
* ConnectBox Ansible roles are updated to build ConnectBox with Moodle, PHP and MySQL
* TheWell is for Debian OS (Raspbian) on Raspberry Pi (with modifications) or other Linux host
* Refer to Relay Trust Moodle Repo for Documentation Of Changes
* Default Moodle MySQL database is located in this repo under ansible/roles/moodle/templates/
* Legacy Connectbox File Serving is now at {{{hostname}}} such that Connectbox is http://thewell, Moodle is http://learn.thewell and Admin is http://thewell/admin
* (There will be more as this gets built out)

## mmiLoader — USB Content Indexer

`mmiLoader.py` (deployed to `/usr/local/connectbox/bin/mmiLoader.py` by the `bootstrap` role) scans USB content and builds the JSON/file structure used by the enhanced media interface.

### USB insert behaviour

| Scenario | Behaviour |
|---|---|
| First insert or no `saved.zip` | Full index walk — scans all files, extracts thumbnails, writes JSON, creates `saved.zip` at end |
| Re-insert same USB key | `saved.zip` found, mtime matches cached marker → `unzip -n` skips files already on disk (fast) |
| Swap to different USB key | `saved.zip` found, mtime differs → wipes content directory, full extract, writes new marker |
| `saved.zip` deleted from USB | Falls through to full index walk |

To force a full re-index on a USB key that already has `saved.zip`, delete `saved.zip` from the USB drive.

### OLED display messages during indexing

| Message | Meaning |
|---|---|
| `Loading USB` | Checking for `saved.zip` |
| `Unzipping USB` | Restoring from `saved.zip` (fast path) |
| `Indexing USB` | Full index walk in progress |
| `Creating ZIP File` | Compressing a web archive directory |
| `Highly Complex Filesystem` | Complex HTML directory structure detected |

### Video thumbnail extraction

Thumbnails are extracted from video files using `ffmpeg`. mmiLoader tries frames at 15 s, 30 s, 1 min, 2 min, and 3 min, skipping any frame that is predominantly black, white, or a near-uniform solid colour (detected via grayscale mean and standard deviation). The first usable frame is saved as a hidden `.thumbnail-<lang>-<slug>.png` on the USB drive so it is not re-extracted on subsequent runs.

### Language support

Regional language variants (e.g. `zh-CN`, `pt-BR`) on the USB are handled by aliasing the base code (`zh`, `pt`) to the full variant directory. The media interface always requests content using the base code, so this symlink ensures the correct content is served.

### Single-instance guard

mmiLoader uses `pgrep` at startup to prevent concurrent duplicate runs. `PxUSBm.py` (the USB monitor daemon) also guards each mmiLoader launch site with `pgrep` and sets a sentinel after a successful index to avoid re-triggering on every poll cycle.

# ConnectBox

ConnectBox is a media sharing device based on small form factor computers including the Raspberry Pi 3, Raspberry Pi Zero W, NanoPi NEO, Orange Pi Zero and Pine64.

# Making a ConnectBox

See [docs/deployment.md](docs/deployment.md)

# Making a Connectbox on AWS

See [docs/awsinstall.md](docs /docs/awsinstall.md)

# Connectbox setup and administration

See [docs/administration.md](docs/administration.md)

# Developing the ConnectBox Software

See [docs/development.md](docs/development.md)

# MicroSD Card Images/Releases
TBD
