# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

ConnectBox is an offline media-sharing appliance for Raspberry Pi and similar SBCs (NanoPi NEO, Orange Pi Zero 2, Radxa CM3). It creates a WiFi access point with a captive portal, serves media from a USB drive via an enhanced web interface, and optionally includes Moodle LMS. The entire system is provisioned via Ansible onto a target device running Raspbian/Debian.

## Provisioning

```bash
# Install Python/Ansible dependencies
pip install -r requirements.txt

# Provision a connected device - run from ansible/ so ansible/ansible.cfg applies
# (force_handlers, pipelining); see docs/deployment.md
cd ansible && ansible-playbook -i <device_ip>, site.yml -e wireless_country_code=US

# Resuming a stopped build: --start-at-task skips site.yml's pre_tasks, so pass
# their variable files yourself
ansible-playbook -i <device_ip>, -e @group_vars/debian -e @group_vars/brand \
  -e @group_vars/armbian site.yml --start-at-task "<task name>"

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
| `usb-content` | systemd-udevd drop-in; removes the retired `99-usb-automount.rules` udev rule. USB mounting itself is done by `PxUSBm.py` (see USB content pipeline) |

### Source file naming convention

Files in `ansible/roles/bootstrap/files/` use underscores to encode their deploy path. `usr_local_connectbox_bin_mmiLoader.py` deploys to `/usr/local/connectbox/bin/mmiLoader.py`. Edit the repo file, then `scp` to device for testing before committing.

### Comment Policy

all functions should have comprehensive comments explaining what the function does

Each major loop or section in a file should have a comment explaining what it does, what the logic is and why it is done this way


### Brand configuration

Device configuration is stored as JSON in `/usr/local/connectbox/brand.j2`. This is the single source of truth — `brand.txt` has been eliminated. `ConnectBoxManage.sh` uses `jq` to read/write it. The Node.js backend (`/var/www/enhanced/connectbox-manage/src/`) also reads it directly.

The front panel re-reads brand.j2 on every pass of its main loop, so it must never be seen half written: the hat service crashed (2026-10-26) reading an empty brand.j2 while a copy command rewrote it. Every writer writes a temporary file and renames it into place, keeping owner and mode: hat service `globals.write_brand()` (readers use `globals.read_brand()`, which retries for ~2 s), PxUSBm `write_brand_file()`, connectbox-manage `setBrand`. Keep it that way for any new writer.

### USB content pipeline

1. USB inserted → `PxUSBm.py` (the only USB mounter, a service polling `lsblk` every ~3 s) mounts it at `/media/usb0`, then on its next poll starts `mmiLoader.py` in the transient `connectbox-loader` systemd unit (`/tmp/.usb0_indexed` stops it re-running). It mounts the first partition (`sda1`) or a whole disk that holds a file system with no partition table (`mkfs.ext4 /dev/sdb`); Linux file systems are mounted without the FAT-only `utf8` option and skip `dosfsck`. On removal it stops the loader, empties the Kiwix library, clears the menus (`mmiLoader.py --clear` -> `clear_menus()`: empty English template, footer, default languages.json; never touches `/media/usb0`) and lazily unmounts `/media/usb0`. Before this, menus built for a USB stayed listed after it was pulled. Do not reintroduce a udev mounter (`usb_mounter.py` was retired 2026-10-05) — two mounters race. Likewise PxUSBm owns network recovery (AP/client interface checks, `hostapd` restarts); and first-boot partition expansion; the hand-installed `network-watchdog` and `first-boot-expand` were retired 2026-10-05 for racing it. `system_scripts/` now only documents what was retired plus systemd restart overrides. Simulation tests: `ansible/roles/bootstrap/files/test_PxUSBm_mount.py`.
   - **The box's own content** lives in `/media/usb0/content` on the SD card (put there by the front panel's "copy from USB"). A key plugged in is mounted on top of `/media/usb0` and shown instead. With no key at `/media/usb0`, `check_internal_content()` (called after every `mountCheck()`) starts the loader once for the own content (marker `/tmp/.internal_indexed`; it waits 20 s after PxUSBm starts so a plugged-in key is mounted first); pulling a key out of usb0 removes the marker, so the box goes back to its own content. mmiLoader's `usb_is_present()` follows the same rule: a run that started with a key mounted stops when the key goes; a run on the own content continues while `/media/usb0/content` exists.
   - If `/media/usbN` no longer has the device PxUSBm put there (the front panel's copy commands move a key to `/media/usb11` and back), PxUSBm forgets that slot (for usb0 also `/tmp/.usb0_indexed`), so the key comes back at usb0 instead of being booked at usb0 and mounted again at usb1.
   - `dosfsck`/`ntfsfix` are never run on a mounted device (Linux marks a mounted FAT key dirty, and `dosfsck -a` then "repaired" it while in use). NTFS mounts through ntfs-3g (FUSE); the explicit `-t ntfs` retry no longer uses `sync` (about 0.1 MB/s writes with it on a NanoPi, about 9 MB/s without).
   - **Check before mount, by type** (2026-10-29): FAT -> `dosfsck -a` only when `fat_needs_check()` says the volume was not unmounted cleanly or recorded an I/O error (FAT[1] flags as Windows sets them, boot-sector state bit 0 as Linux sets it; unreadable boot sector -> check); NTFS -> `ntfsfix -d`; exFAT/other -> none. `run_fs_check()` stops a check after `FS_CHECK_SECS` (120 s) and mounts anyway (dosfsck without `-w` writes its repairs only at the end); a full dosfsck of a 64 GB FAT32 card took over 14 minutes on a NEO, and PxUSBm does nothing else (Wi-Fi watching included) while it waits. Meanwhile PxUSBm refreshes `/tmp/connectbox-usbcheck.txt` ("Checking USB") every 5 s; the hat service shows it as a wait page while fresh (<15 s), without counting it as indexing (no checkmark). A large key pulled out without unmounting stays dirty, so it waits the 2 minutes on every insert.
   - **PxUSBm restarts**: it starts with empty mount tables and does not adopt mounts made before; `release_usb_slots()` (just before the first mount check) lazily unmounts every `/media/usb0`-`usb9` mount and removes `/tmp/.usb0_indexed`, so present keys are mounted, checked and indexed afresh (before this, a key pulled out across a restart left a dead mount and the next key was mounted on top of it). `mounted_device()` returns the last `/proc/mounts` entry for a folder (the mount in use when stacked); `clear_dead_mounts()` removes mounts whose device node is gone before mounting into a slot. Its first mount check comes about 2 minutes after a (re)start: it resets the Wi-Fi first (dhclient on the client interface waits up to 60 s) and then pauses 30 s.
   - Before each first-boot expansion reboot `end_client_dhcp_wait()` ends dhclient on the Wi-Fi interfaces: ifup for the client interface was still in dhclient (no client network, 60 s timeout) holding `/run/network/ifstate.wlanN`, so the reboot waited up to a minute on "A stop job is running for ifup for wlan0".
   - PxUSBm's own log is `/var/log/PxUSSBm.log` (the name has two S); the journal has only its stdout.
   - On file systems with Unix permissions (ext2/3/4, xfs, btrfs, f2fs) `mmiLoader.py` first runs `make_usb_world_readable()` — the equivalent of `chmod -R a+rX` that skips symlinks and only touches entries missing bits — so nginx (`www-data`) can read files written by another computer's user account. FAT/exFAT/NTFS are left alone.
2. `mmiLoader.py` removes the old content directory, then checks for `saved.zip` on the USB (`content/` or USB root):
   - **Found**: extract it in full into `/var/www/enhanced/content/www/assets/content/`, refresh interface translations and RTL flags, exit (no indexing)
   - **Missing**: full index walk — scans files, extracts thumbnails via ffmpeg, generates JSON, writes `saved.zip` at the end
3. Thumbnails stored as hidden files on USB (`.thumbnail-<lang>-<slug>.png`) to avoid re-extraction

Force a full re-index by deleting `saved.zip` from the USB.

### Admin and stats backend

Port 5002: Node.js (`/var/www/enhanced/connectbox-manage/src/index.js`) managed by PM2. This is the `connectboxmanage` CLI target — all `get`/`set` calls go through HTTP to this process. If port 5002 is down, `connectboxmanage` throws a traceback instead of JSON. It runs on Node.js 22 LTS (v22.23.4, support until 2027-04-30), installed by the enhanced-content role from the nodejs.org linux tarball into /usr/local (pm2 in /usr/local/lib/node_modules; the pm2-root service points there). Node 24 and later have no 32-bit ARM build and NodeSource's armhf packages stop at 22.15.0, so the NEO cannot go past Node 22 this way. Until fix 60 (2026-10-29) it was Node 16 from NodeSource apt.

Port 5000: Python gunicorn serving `python/main.py` (chat + admin API Flask app).

Port 5001: Python captive portal.

### Front panel (OLED and buttons)

The hat service (sibling repo `connectbox-hat-service`, installed with pip from GitHub master into `/usr/local/connectbox/battery_tool_venv`) runs the OLED and buttons. Its admin commands (`buttons.py`: copy from USB, copy to USB, erase) stop the content loader and kiwix-serve to free the key, and afterwards restart kiwix-serve if it is enabled. While copying the wait page shows `Copying 45%` and the size (`_copyWithProgress`: a watcher thread compares the destination's free space with its value at the start, every 3 s, never 100% before the copy returns). After a copy or erase that changes the box's content, the command hands over to the main loop (`hat.indexPending`); the loop shows the loader's status and ONE success page when `connectbox-loader` has finished (before, two checkmarks appeared). The command lets PxUSBm start the re-index (it clears `/tmp/.internal_indexed`) and starts the loader itself only if that has not happened within 30 s. Button presses on a wait page are ignored (they used to re-run the last command).

`/tmp/creating_menus.txt` is the panel's status text from mmiLoader (only mmiLoader writes it). While it exists the panel shows it as a wait page, e.g. `Indexing 45%` / `of 778 files` (mmiLoader `processing_message()`, two lines of at most 15 characters, no file names). mmiLoader writes nothing once it has received SIGTERM and removes the file on any exit if it still holds what that run wrote (`remove_own_status`, atexit). The panel removes a file that has not changed for 15 s while no `mmiLoader.py` process is running (`statusFileStale()`), so a stopped run can no longer leave "Indexing USB" on the screen. `neo-battery-shutdown.service` sets `PYTHONUNBUFFERED=1` so the service's `print()` output reaches the journal as it happens.

### Shutdown service

`neo-battery-shutdown.service` runs `/usr/local/connectbox/battery_tool_venv/bin/neo_batterylevelshutdown`. Left button held ≥4 s → `shutdownDevice()` → `/usr/local/bin/poweroff/poweroff` (symlink to `shutdownShell.sh`) → `shutdown.sh` (Python: sets AXP209 register 0x32 bit 7 via i2c, then calls `/sbin/shutdown -h now`). The i2c bus is 0 for NEO, 10 for CM4.

## Device access

SSH config at `~/.ssh/config` has wildcard for `192.168.1.*` using `root` + `id_ed25519`. The WiFi MAC address is deliberately rotated at least on every boot, so a device's IP changes on every boot (and when PxUSBm brings WiFi back up). This is by design; don't try to pin it. The wired eth0 MAC is the opposite: on the NanoPi NEO it is fixed (fix 63) by `/etc/udev/rules.d/72-connectbox-fixed-eth-mac.rules` + `fixed_eth_mac.sh` (02 + SHA-256 of the chip ID), because it is the box ID used by phonehome and the admin page; before that the kernel picked a random one each boot (the NEO device tree has no ethernet0 alias). /etc/machine-id is the same on every box made from the image, so it is not a box identity. Get the current IP from the OLED or the router. Direct SSH: `ssh root@<device_ip>`. Build Pi: `ssh build`.

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
- `6.js` `goToDetails` — HTML items open via `window.location.href` instead of the detail page (except Word documents, which open the detail page like PDFs). Because that skips the detail page (where the stock app reports views), the patch sends the view report itself (`PUT /admin/api/weblog`, same body as `StatReporterProvider`, honours `disable_stats`). The function is replaced by brace matching, so it upgrades older patched copies too.
- `3.js` `MediaDetailPage.prototype.loadData` — on a language change, `popToRoot()` before `setLanguage()` (prevents "media missing!" and blank pages)

- `6.js` language button — shows the active language's own name (`patch_language_button.py`)
- `6.js` footer — the "Configuration" admin link uses `FOOTER_CONFIGURATION` from the language's interface.json (`patch_footer_translation.py`)
- `2.js` + `main.css` chat page — translated labels (`CHAT_*`), right-to-left message direction, bubble placement (`patch_chat_rtl.py`, reproduces edits first made by hand on the test unit)
- every bundle with `DownloadButtonComponent` (0/1/3/4/5/7.js: detail page and viewers) — the download button shows the file size ("412 MB") from a HEAD request made when the button first sees its file path; nothing is shown if the size is unknown or nginx answered with the app's index.html (missing file) (`patch_download_size.py`)
- `main.js` LanguageProvider — a returning visitor's saved language is rebuilt from the current languages.json so `rtl` changes reach them (`patch_saved_language.py`)
- `main.js` LanguageProvider — a first-time visitor (no saved language) starts in the first of the browser's languages (`navigator.languages`, i.e. its Accept-Language list) the box has: exact code, else same base language, per browser language in order; otherwise the languages.json default. Upstream disabled the browser lookup in mediainterface 70a4923 (2023-07-19, no reason given). A language picked in the menu is saved and always wins (`patch_browser_language.py`)

The `patch_*.py` scripts in `ansible/roles/enhanced-content/files/` are idempotent and exit non-zero when the stock text is missing. `patch_admin_login.py` also recognises a connectbox-admin-ui release that already does a step itself (built from source since 2026-10) and then changes nothing and exits 0. The `3.js` patch matches an exact compiled string with `ignore_errors: yes`, so it silently no-ops if a new mediainterface release changes the code. Inside these `shell: |` blocks YAML strips the block's indentation, so string literals end up less indented than the compiled JS (which uses 4/8 spaces) — test a patch against the real release `6.js`/`3.js` before relying on it. Recheck them after any mediainterface upgrade. **Every push to connectbox-mediainterface `main` rebuilds and republishes its `latest` release** (GitHub Actions), which is what new boxes install - treat a push there as a release, and run all `patch_*.py` against the new `build/` (on Linux; some scripts rewrite line endings on Windows) before relying on it. Releases built in the ConnectBox repo carry `/home/runner/work/connectbox-mediainterface/connectbox-mediainterface/` in template comments (RT's were `.../mediainterface/mediainterface/`); patches must not depend on that folder (`patch_chat_rtl.py` reads it from `2.js`).

## Tests

`ansible/roles/bootstrap/files/test_mmiLoader.py` covers the mmiLoader helper functions (loads the file via `importlib.util.spec_from_file_location`; kept Python 3.7 compatible with `contextlib.ExitStack`). Run it after any mmiLoader change. `test_PxUSBm_mount.py` (same folder) simulates `PxUSBm.mountCheck()` with fake `lsblk` output and the matching `/proc/mounts` — run it after any change to USB mounting.  Both pass in full (2026-10-28: 301 and 32); test_mmiLoader's Word-document tests need `pip install mammoth==1.13.0`.  `test_RestartWLAN.py` is not a unit test (it restarts Wi-Fi on a real box); `tests/test_connectbox_static.py` checks a live box over the network.

## ZIM files (Kiwix)

ZIM files (offline websites: Wikipedia, Stack Exchange, LibreTexts...) are served by `kiwix-serve` (role `kiwix`: kiwix-tools 3.8.2, `linux-armv6` build on 32-bit ARM, `linux-aarch64` on 64-bit; service `kiwix-serve` as www-data on 127.0.0.1:8090, `--urlRootLocation=/kiwix --monitorLibrary`). nginx proxies `location ^~ /kiwix/` to it (with the home button).

- **Library:** `/var/lib/connectbox/kiwix/library.xml`. mmiLoader rebuilds it from the USB's `.zim` files on every insert (`rebuild_kiwix_library()`, before both the saved.zip restore and a full index — the library lives on the device). PxUSBm empties it when usb0 is removed. kiwix-serve picks changes up within ~2 s; no restart. The library is built in `library.xml.new` and swapped in with one rename (writing the live file once per ZIM let kiwix-serve load a half-built library and miss the last book for good); `ensure_kiwix_serves()` then checks kiwix-serve's catalog (`/kiwix/catalog/v2/entries`) and restarts it if a book is still missing after ~10 s.
- **Cards:** each `.zim` becomes a stand-alone web-content card (`mediaType: html`, `mimeType: application/x-zim`), even inside a collection folder: title, description and icon come from the ZIM's library entry; `html/<slug>/index.html` redirects to `/kiwix/content/<zim file name without .zim>/`. The detail page's download button is hidden for ZIM cards (`patch_zim_download.py`).
- **Card icons:** from the ZIM's favicon via `card_icon_png()` (pure-Python PNG decode/encode, no PIL on devices): an empty icon (<2% visible pixels, e.g. Open Music Theory's) falls back to `www.png`; a dark icon on a transparent background (>=15% transparent, visible luminance <0.35) is flattened onto white so it shows on the dark cards; others are kept as they are.
- **Languages:** the folder decides. A multi-language ZIM (library `language` like `eng,fra`) is also listed in its other tagged languages that the box has; a single-language ZIM in another language's folder only gets a log note. TED ZIMs (`_category:ted`, ted2zim) pick their language from `localStorage["ted2zim.selectedLanguage"]` and default to English, so their card's redirect page stores the card's language there first (lower-cased box code, e.g. `zh-cn`; only a language the ZIM is tagged with) - `ted_start_language()`. Kiwix is proxied on the same host, so the page and the ZIM share localStorage.
- New ZIMs on a stick that has `saved.zip` appear only after `saved.zip` is deleted (same as any new content).
- Caching: for Kiwix HTML only, nginx replaces Kiwix's `Cache-Control: max-age=3600` and book-level ETag with `no-cache` (maps `$kiwix_cache_control` / `$kiwix_etag`), because nginx changes the page (home button) and browsers would otherwise keep old copies. Other ZIM files keep Kiwix's caching.

## Same file name in different folders

Each language has one flat `media/` folder of links, and a card's slug comes from its file name, so two files with the same name in different folders used to share a link, a data file and a thumbnail (the second card played the first file). `unique_media_name()` in mmiLoader keeps the first file's name; a later file with the same name shares it if it is an identical copy (same size, same first/last 64 KB), otherwise it gets `<name>--<folder><ext>` (then `-2`, `-3`...) as its link name and slug. The card title stays the original file name. Files that never collide keep their names, so slugs, usage stats and cached thumbnails are stable.

## Word documents and spreadsheets as web pages

`make_document_web_page()` in mmiLoader (table `WEB_PAGE_CONVERTERS`: `.docx`, `.xlsx`, `.xls`, `.pptx`) converts each `.docx` (mediaType `document`) with mammoth (bootstrap role, `mammoth==1.13.0`) into `<lang>/html/<slug>/index.html` plus `imageN.*` (no download link on the page; the original stays in `<lang>/media/`), and turns the card into `mediaType: html` while keeping the Word mimeType. The app opens html items at `html/<slug>/`. Word cards, single or in a collection, go to the detail page like PDFs (the `goToDetails` patch skips them); there `patch_zim_download.py` points the download button of Word items at the original `media/<fileName>` instead of the non-existent `html/<slug>.zip`, and gives their open button the book icon used for PDF/EPUB instead of the web-page "exit" icon, and opens the Word page in the same tab (stock code calls `window.open` after an async view report, which old browsers block as a popup). A collection of Word files keeps `mediaType: document` (an html collection card would open a non-existent `html/collection-<name>/`). Missing mammoth or a failed conversion leaves the old download-only card. Image descriptions that are file paths are dropped (`docx_alt_text`). `.docx` cards and collections use `docx.png` (DOCX label, made from `doc.png`); old `.doc` keeps `doc.png`. Spreadsheets: `.xlsx` with openpyxl (read-only streaming, `data_only` so formulas show their saved result) and `.xls` with xlrd (`openpyxl==3.1.5`, `xlrd==2.0.1`, bootstrap role); one table per visible sheet, first row as header, numbers right-aligned, cut at `SHEET_MAX_ROWS` (2000) rows / `SHEET_MAX_COLUMNS` (100) with a language-neutral "⋯ shown / total" line; icons `xlsx.png` / `xls.png`. Presentations: `.pptx` read with zipfile + ElementTree only (`convert_pptx_to_html`): slide order from `ppt/presentation.xml`, hidden slides (`show="0"`) skipped, title placeholder as heading, body placeholders as bullets (levels kept), text boxes as paragraphs, pictures copied (browser formats only; EMF/WMF dropped), tables, groups and `mc:Fallback` looked into, speaker notes from the notes slide body under `page_string(language, "SLIDE_NOTES")` (translated via `set_page_strings_config(config)` set at the start of a run). Icons `pptx.png` / `ppt.png`. Old binary files: `.doc` with antiword (`-x db` DocBook output; no pictures; documents in the OLE mini-stream, under ~300 characters, stay download-only) and `.ppt` with olefile 0.47 plus mmiLoader's own [MS-PPT] record reader (current edit, slide order, shape text, bullet levels, speaker notes; no pictures). A `.doc`/`.ppt` with a same-named `.pdf` in its folder (any case, `has_same_named_pdf()`) is not converted and stays a download (Kirk's rule). Both tools are installed by the bootstrap role; without them the files stay download-only. The stock `types.json` has no `.pptx`/`.ppt`, so the Ansible types.json task adds them (without it presentations are skipped). The patches (`patch_zim_download.py`, `goToDetails`) treat the spreadsheet mimeTypes like Word. A folder is a collection only with more than two files (`directoryType`).

## Home button on web content

Pages inside web content (and, later, ZIM files) have no way back to the menu, so nginx adds a floating house button before `</body>` as each HTML page is served (`ansible/roles/nginx/files/connectbox_home_button.conf`, included from the web-content location). It needs the `subs_filter` module (`libnginx-mod-http-subs-filter`; nginx-light has no `sub_filter`) and `include /etc/nginx/modules-enabled/*.conf;` in nginx.conf, which the template previously lacked. For a proxied backend such as kiwix-serve, set `proxy_set_header Accept-Encoding "";` so the upstream HTML is uncompressed, and use `location ^~ /kiwix/` - otherwise the vhost's `location ~ \.json$` regex takes `.json` requests away from the proxy.

## Interface translations

The app's UI strings (`<lang>/data/interface.json`) exist only in English upstream. mmiLoader writes each language's file from `/usr/local/connectbox/translations/<code>.json` (shipped from `ansible/roles/bootstrap/files/translations/`: 46 files covering Kirk's top-50 spoken languages, because boxes are normally offline; fa, ar, es, pt, zh-CN were reviewed earlier; every string added 2026-10-26 says "native check advised" in its `source` field). Language folders map to files with `TRANSLATION_CODE_ALIASES` (arb→ar, pes→fa, cmn/wuu/cjy/hak→zh-CN Simplified, yue→zh-HK Hong Kong Traditional, nan→zh-TW Taiwan Traditional); Egyptian Arabic has its own `arz.json`. `EXTRA_PHONE_CODES` adds the codes phones report for a language (arz: ar-EG; pnb: pa-PK, pa-Arab; tl: fil; id: in), and languages.json `codes` lists the folder code first, then those (`phone_codes()`), for the app's browser-language start and the loading page. The captive portal's text (`PORTAL_*` strings, in `EXTRA_INTERFACE_STRINGS`) is kept in the same files: the portal (`simple-offline-captive-portal`, `translations.py`) reads `/usr/local/connectbox/translations/` and languages.json and shows its page in the first Accept-Language language the box has (exact, then base language), else the box's default, else English; right-to-left languages are laid out RTL. `PORTAL_USE_AS_IS` must be Android's own wording of "Use this network as is" (AOSP CaptivePortalLogin); for languages Android lacks the English label is used and the text says top right. For any other language it looks the strings up online (MyMemory) when the box has internet and saves them there; offline it falls back to English and retries next time. Each entry keeps the English it was translated from, so changed English is re-translated and hand corrections to `text` stick. Codes are normalised via languageCodes.json (`per`→`fa`, `ara`→`ar`): identical English name lists first, else the one 2-letter code sharing a name (`spa` "Castilian, Spanish"→`es` "Spanish"); the same mapping places multi-language ZIMs (Kiwix tags are 3-letter). Right-to-left languages get `"rtl": true` in languages.json. After a `saved.zip` restore, `refresh_interface_translations()` rewrites interface.json and the rtl flags. MyMemory output for short UI strings is often wrong (it is partly crowd translation memory) — review new languages before shipping them. mmiLoader is the only writer of interface.json (`apply_translations.py` was retired).

## Broken links in web content

`connectbox_enhanced.conf.j2` sends a 404 under `/assets/content/<lang>/html/` back to the start page of the item it was clicked in (taken from the `Referer`), or to `/` if there is no item or the start page itself is missing. Without this, the server-wide `error_page 404 /index.html` served the app's page at the wrong address and readers got a blank page. Behaviour was verified with real nginx (Windows build, same map/PCRE) against a mock content tree.

## OpenWell (content packages)

A live feature, not a The Well leftover - keep it. Boxes can load menus and media from a server package instead of a USB: admin Web Server section -> connectbox-manage (`get.subscriptions`, `set.subscribe`, `doCommand.openwellrefresh`, `doCommand.openwellusb`) -> `/usr/local/connectbox/bin/lazyLoader.py` (installed from connectbox-mediainterface `main`). Server side: connectbox-chathost `/chathost/link/openwell` -> MediaBuilder (Bolt). Subscribing only writes `assets/content/subscription.json`; downloads happen only when the admin presses "Download Missing Content Files" (no cron). "Load Content From USB Flash" also serves as a manual full re-index (deletes `saved.zip`). Details in README "OpenWell".

## Important invariants

- **dhcpcd must not manage the WiFi client interface**: `denyinterfaces` in `etc_dhcpcd.conf.j2` is a global option and must come before any `interface` block (inside one it is ignored, and the box got two IPs from dhcpcd + dhclient). Never release/reconfigure `wlan1` live over SSH on that link (`dhcpcd -k wlan1` dropped the box off the LAN) - apply network changes with a reboot.
- **Captive portal must support very old phones**: devices are deployed in disadvantaged countries with iOS 9 / Android 4–5 era phones. The old-OS checks in `captiveportal/views.py` (sibling repo `simple-offline-captive-portal`) are intentional — do not remove or "modernize" them.
- **Video must be H.264 in MP4**: browsers don't play MPEG-4 Part 2 (`mp4v`). `content["mimeType"]` must be the real MIME type (`video/mp4`), not the media type (`video`).

- **Line endings**: All `.sh` and `.py` files must have Unix LF endings. `.gitattributes` enforces this. CRLF causes `#!/bin/bash^M: bad interpreter` on the device. Check with `cat -A <file> | head -1` — should show `$` not `^M$`.
- **brand.j2 is JSON**: Any script that writes to `brand.j2` must produce valid JSON. `node -e "JSON.parse(require('fs').readFileSync('/usr/local/connectbox/brand.j2'))"` to verify.
- **Admin (Configuration) login does not persist** (Kirk's decision: a phone left logged in as admin is dangerous in some countries). connectbox-manage ends a session after 5 minutes without an admin request (`ADMIN_IDLE_MS`, also the cookie's maxAge; `req.session.seen` checked by the auth guard) and on `GET`/`POST /admin/api/logout`; the admin page calls `/admin/api/keepalive` once a minute while open. `patch_admin_login.py` (enhanced-content role, patches the connectbox-admin-ui release bundles; the same changes are in the admin-ui source) makes Exit go to the main ConnectBox screen, makes Configuration always ask for the password (the admin page only opens when reached from another /admin page), logs out when the login page opens and when the admin page is left (sendBeacon), sends Reload/Back/Forward to the login page, and removes the "Default password is..." text. Do not add a long-lived admin cookie.
- **No shell with user input in password handling**: connectbox-manage checks the admin password with `execFileSync('openssl', ['passwd','-apr1','-salt','CBOX2018','-stdin'], {input})` and a constant-time compare, and rejects empty, non-string and multi-line passwords; `set.password` and `ConnectBoxManage.sh` (`printf '%s\n' "$val"`) do the same. The old code put the password in a shell command line. Other `functions.js` setters still build shell commands from their input (behind the admin login).
- **Admin session key is per box**: connectbox-manage signs admin login cookies with a random key it creates on first start in `/usr/local/connectbox/admin_session.key` (root, 600). Never put a fixed key back in the source (the old published key allowed forged admin logins), and keep the image-preparation task that deletes the file so image-made boxes don't share a key.
- **"Loading new content" page**: mmiLoader writes `/tmp/connectbox-indexing.html` during a full index only (`start_indexing_page`, progress via `indexing_progress`, removed before saved.zip is written, by atexit/SIGTERM/`--clear`; PxUSBm removes a leftover one at start if no mmiLoader runs). nginx (`connectbox_enhanced.conf.j2`) rewrites `/` and `/index.html` to it while it exists. Do not key it on `/tmp/creating_menus.txt` - that is the front panel's status file (see Front panel). Web-content folders count as one item in the progress total. The page holds the message in every language on the USB (`set_indexing_languages`, after `detect_language_dirs`) from the `INDEXING_TITLE`/`INDEXING_TEXT` interface strings (EXTRA_INTERFACE_STRINGS + shipped translations), but shows only one: a small script matches each message's `data-code` (the language's codes, `phone_codes()`) against `navigator.languages`, exact code first, then base language; otherwise (or without JavaScript) the default language. Progress is language-neutral "N / M". The page refreshes to `/?reload=<time>` and nginx sends `/` and `/index.html` with `Cache-Control: no-cache`: before that, browsers had heuristically cached the start page (2023 Last-Modified, no Cache-Control) for months, so a plain meta refresh showed the cached app and the menu never appeared by itself.
- **mmiLoader single-instance guard** is the marker file `/tmp/creating_menus.txt` (written by `initialize_run`, removed at the end of a run, by the SIGTERM handler, at exit by `remove_own_status`, by `--clear`, and by PxUSBm at start-up when no `mmiLoader.py` is running). At start, if the file exists mmiLoader checks `/proc/*/cmdline` for another `mmiLoader.py` run (not `--clear`): if there is one it exits, otherwise the file is a leftover and is removed.
- **No PxUSBm during a build**: the bootstrap role creates `/run/connectbox-build`; while it exists the cron job `TestPxUSBm.py` does not start PxUSBm (its first start on a fresh card expands the partition and reboots twice, which once cut a build off mid-upgrade). The connectbox-pi role removes it at the end unless the build prepares an image; `/run` is cleared at every boot.
- **Default language**: mmiLoader's `mark_default_language()` makes the entry with an `en`/`eng`/`en-…` code the default in `languages.json`, else the first entry; it also runs after a saved.zip restore (`refresh_interface_translations`), so old zips are corrected.
- **Zips stop on SIGTERM**: mmiLoader makes every zip with `make_zip()` (not `shutil.make_archive`, which ignores the stop flag, so `systemctl stop` waited 90 s and killed the loader). It writes `<name>.zip.part`, renames it when complete and removes it when stopped.
- **USB control files run as root** (kept by Kirk's decision, 2026-10-28): PxUSBm enables SSH for `.connectbox/enable-ssh` and runs `.connectbox/upgrade/upgrade.py` as root from any USB mounted at usb0. Known risk; documented in docs/mmiLoader-usb-structure.md section 5.
- **saved.zip is written last**: `mmiLoader.py` checks `os.path.ismount("/media/usb0")` at each directory iteration and before writing `saved.zip`. If USB disconnects mid-run it exits cleanly without corrupting the content directory.
