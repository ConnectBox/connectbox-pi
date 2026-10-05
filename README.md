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
| No `saved.zip` on the USB | Full index walk — scans all files, extracts thumbnails, writes JSON, creates `saved.zip` at end |
| `saved.zip` on the USB (in `content/` or the USB root) | Content directory is wiped and `saved.zip` is extracted in full (fast); no indexing |
| `saved.zip` deleted from USB | Falls through to full index walk |
| USB removed | Menus are cleared to the empty English page (`mmiLoader.py --clear`, run by PxUSBm) and Kiwix stops serving the USB's ZIM files |

After a `saved.zip` restore, mmiLoader also rewrites every language's `interface.json`
(translations) and the right-to-left flags in `languages.json`, because the zip holds the
versions from when it was made.

To force a full re-index on a USB key that already has `saved.zip`, delete `saved.zip` from the USB drive.

### OLED display messages during indexing

| Message | Meaning |
|---|---|
| `Checking USB Permissions` | Linux-formatted USB (ext4 etc.): making files readable by the web server |
| `Loading USB` | Checking for `saved.zip` |
| `Unzipping USB` | Restoring from `saved.zip` (fast path) |
| `Indexing USB` | Full index walk in progress |
| `Creating ZIP File` | Compressing a web archive directory |
| `Highly Complex Filesystem` | Complex HTML directory structure detected |

### Video thumbnail extraction

Thumbnails are extracted from video files using `ffmpeg`. mmiLoader tries frames at 15 s, 30 s, 1 min, 2 min, and 3 min, skipping any frame that is predominantly black, white, or a near-uniform solid colour (detected via grayscale mean and standard deviation). The first usable frame is saved as a hidden `.thumbnail-<lang>-<slug>.png` on the USB drive so it is not re-extracted on subsequent runs.

### Language support

Regional language variants (e.g. `zh-CN`, `pt-BR`) on the USB are handled by aliasing the base code (`zh`, `pt`) to the full variant directory. The media interface always requests content using the base code, so this symlink ensures the correct content is served.

Language folders and `.language` may use 2- or 3-letter codes; `per` and `fa` are both Farsi, `ara` and `ar` both Arabic. Right-to-left languages (Arabic, Farsi, Hebrew, Urdu, ...) are flagged `"rtl": true` in `languages.json`, which flips the interface. The language button on the home page shows the active language's own name (e.g. فارسی).

### Interface translations

The app's own text (section titles, media types, the footer's Configuration link, chat labels) comes from each language's `interface.json`. Upstream only has English, so mmiLoader writes each language's file from `/usr/local/connectbox/translations/<code>.json`:

1. Reviewed files are shipped by Ansible for Farsi, Arabic, Spanish, Portuguese and Chinese (`ansible/roles/bootstrap/files/translations/`).
2. For any other language, if the box has internet, the English text is translated online (MyMemory) and saved there, so it keeps working offline afterwards.
3. With no internet, English is shown and the lookup is retried on the next USB insert.

Online translations of short interface words are often poor; check new files in `/usr/local/connectbox/translations/` and correct the `text` values (corrections are kept). A string is re-translated only when its English changes.

### Web content and ZIM pages: getting back to the menu

Every page inside web content (HTML folders) and ZIM files shows a small round house button in the bottom-left corner that returns to the ConnectBox menu in the visitor's language. nginx adds it as pages are served; the content itself is not changed. Links inside web content that point to pages missing from the USB go back to that item's start page instead of a blank page.

### ZIM files (offline websites)

Put `.zim` files (from https://library.kiwix.org) in a language folder on the USB, e.g. `content/en/wikipedia_en_100_2025-01.zim`. Each one becomes a card in that language with the ZIM's own title and icon (a dark icon is put on a white background so it shows on the dark cards; an empty one is replaced by the standard web icon), and opens in Kiwix; a ZIM tagged with several languages also appears in its other languages that are on the box. Search inside a ZIM is Kiwix's own. Files over 4 GB need an exFAT or ext4 USB. After adding ZIMs to a USB that already has `saved.zip`, delete `saved.zip` so the USB is re-indexed.

### USB file systems

`PxUSBm.py` is the only USB mounter (it polls `lsblk` every ~3 s). It mounts FAT32, exFAT and NTFS sticks, and Linux file systems (ext2/3/4, xfs, btrfs, f2fs), including sticks formatted on the whole disk with no partition table (`mkfs.ext4 /dev/sdX`). Use ext4 or exFAT for files over 4 GB (FAT32's limit).

On Linux file systems, files keep the owner and permissions of the computer that wrote them, which can stop the web server reading them (cards show but open with 403). mmiLoader therefore adds read permission for everyone (like `chmod -R a+rX`, skipping symlinks and never adding execute to files) before indexing. Only files missing permission are changed, so re-inserting the same stick is quick.

### Starting the indexer and single-instance guard

`PxUSBm.py` starts mmiLoader on the poll after `/media/usb0` is mounted, in the transient systemd unit `connectbox-loader`, and stops it when the USB is removed. The sentinel `/tmp/.usb0_indexed` stops it re-running on every poll. mmiLoader refuses to start while a run is in progress, marked by `/tmp/creating_menus.txt` (removed at the end of a run, when the run is stopped, and by `--clear`).

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
