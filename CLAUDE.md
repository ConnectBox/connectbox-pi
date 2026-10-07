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

### USB content pipeline

1. USB inserted → `PxUSBm.py` (the only USB mounter, a service polling `lsblk` every ~3 s) mounts it at `/media/usb0`, then on its next poll starts `mmiLoader.py` in the transient `connectbox-loader` systemd unit (`/tmp/.usb0_indexed` stops it re-running). It mounts the first partition (`sda1`) or a whole disk that holds a file system with no partition table (`mkfs.ext4 /dev/sdb`); Linux file systems are mounted without the FAT-only `utf8` option and skip `dosfsck`. On removal it stops the loader, empties the Kiwix library, clears the menus (`mmiLoader.py --clear` -> `clear_menus()`: empty English template, footer, default languages.json; never touches `/media/usb0`) and lazily unmounts `/media/usb0`. Before this, menus built for a USB stayed listed after it was pulled. Do not reintroduce a udev mounter (`usb_mounter.py` was retired 2026-10-05) — two mounters race. Likewise PxUSBm owns network recovery (AP/client interface checks, `hostapd` restarts); and first-boot partition expansion; the hand-installed `network-watchdog` and `first-boot-expand` were retired 2026-10-05 for racing it. `system_scripts/` now only documents what was retired plus systemd restart overrides. Simulation tests: `ansible/roles/bootstrap/files/test_PxUSBm_mount.py`.
   - On file systems with Unix permissions (ext2/3/4, xfs, btrfs, f2fs) `mmiLoader.py` first runs `make_usb_world_readable()` — the equivalent of `chmod -R a+rX` that skips symlinks and only touches entries missing bits — so nginx (`www-data`) can read files written by another computer's user account. FAT/exFAT/NTFS are left alone.
2. `mmiLoader.py` removes the old content directory, then checks for `saved.zip` on the USB (`content/` or USB root):
   - **Found**: extract it in full into `/var/www/enhanced/content/www/assets/content/`, refresh interface translations and RTL flags, exit (no indexing)
   - **Missing**: full index walk — scans files, extracts thumbnails via ffmpeg, generates JSON, writes `saved.zip` at the end
3. Thumbnails stored as hidden files on USB (`.thumbnail-<lang>-<slug>.png`) to avoid re-extraction

Force a full re-index by deleting `saved.zip` from the USB.

### Admin and stats backend

Port 5002: Node.js (`/var/www/enhanced/connectbox-manage/src/index.js`) managed by PM2. This is the `connectboxmanage` CLI target — all `get`/`set` calls go through HTTP to this process. If port 5002 is down, `connectboxmanage` throws a traceback instead of JSON.

Port 5000: Python gunicorn serving `python/main.py` (chat + admin API Flask app).

Port 5001: Python captive portal.

### Shutdown service

`neo-battery-shutdown.service` runs `/usr/local/connectbox/battery_tool_venv/bin/neo_batterylevelshutdown`. Left button held ≥4 s → `shutdownDevice()` → `/usr/local/bin/poweroff/poweroff` (symlink to `shutdownShell.sh`) → `shutdown.sh` (Python: sets AXP209 register 0x32 bit 7 via i2c, then calls `/sbin/shutdown -h now`). The i2c bus is 0 for NEO, 10 for CM4.

## Device access

SSH config at `~/.ssh/config` has wildcard for `192.168.1.*` using `root` + `id_ed25519`. The WiFi MAC address is deliberately rotated at least on every boot, so a device's IP changes on every boot (and when PxUSBm brings WiFi back up). This is by design; don't try to pin it. Get the current IP from the OLED or the router. Direct SSH: `ssh root@<device_ip>`. Build Pi: `ssh build`.

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
- `main.js` LanguageProvider — a returning visitor's saved language is rebuilt from the current languages.json so `rtl` changes reach them (`patch_saved_language.py`)
- `main.js` LanguageProvider — a first-time visitor (no saved language) starts in the first of the browser's languages (`navigator.languages`, i.e. its Accept-Language list) the box has: exact code, else same base language, per browser language in order; otherwise the languages.json default. Upstream disabled the browser lookup in mediainterface 70a4923 (2023-07-19, no reason given). A language picked in the menu is saved and always wins (`patch_browser_language.py`)

The `patch_*.py` scripts in `ansible/roles/enhanced-content/files/` are idempotent and exit non-zero when the stock text is missing. The `3.js` patch matches an exact compiled string with `ignore_errors: yes`, so it silently no-ops if a new mediainterface release changes the code. Inside these `shell: |` blocks YAML strips the block's indentation, so string literals end up less indented than the compiled JS (which uses 4/8 spaces) — test a patch against the real release `6.js`/`3.js` before relying on it. Recheck them after any mediainterface upgrade. **Every push to connectbox-mediainterface `main` rebuilds and republishes its `latest` release** (GitHub Actions), which is what new boxes install - treat a push there as a release, and run all `patch_*.py` against the new `build/` (on Linux; some scripts rewrite line endings on Windows) before relying on it. Releases built in the ConnectBox repo carry `/home/runner/work/connectbox-mediainterface/connectbox-mediainterface/` in template comments (RT's were `.../mediainterface/mediainterface/`); patches must not depend on that folder (`patch_chat_rtl.py` reads it from `2.js`).

## Tests

`ansible/roles/bootstrap/files/test_mmiLoader.py` covers the mmiLoader helper functions (loads the file via `importlib.util.spec_from_file_location`; kept Python 3.7 compatible with `contextlib.ExitStack`). Run it after any mmiLoader change. `test_PxUSBm_mount.py` (same folder) simulates `PxUSBm.mountCheck()` with fake `lsblk` output — run it after any change to USB mounting.

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

## Word documents as web pages

`make_docx_web_page()` in mmiLoader converts each `.docx` (mediaType `document`) with mammoth (bootstrap role, `mammoth==1.13.0`) into `<lang>/html/<slug>/index.html` plus `imageN.*`, links back to the original in `<lang>/media/`, and turns the card into `mediaType: html` while keeping the Word mimeType. The app opens html items at `html/<slug>/`. Word cards, single or in a collection, go to the detail page like PDFs (the `goToDetails` patch skips them); there `patch_zim_download.py` points the download button of Word items at the original `media/<fileName>` instead of the non-existent `html/<slug>.zip`, and gives their open button the book icon used for PDF/EPUB instead of the web-page "exit" icon, and opens the Word page in the same tab (stock code calls `window.open` after an async view report, which old browsers block as a popup). A collection of Word files keeps `mediaType: document` (an html collection card would open a non-existent `html/collection-<name>/`). Missing mammoth or a failed conversion leaves the old download-only card. Image descriptions that are file paths are dropped (`docx_alt_text`).

## Home button on web content

Pages inside web content (and, later, ZIM files) have no way back to the menu, so nginx adds a floating house button before `</body>` as each HTML page is served (`ansible/roles/nginx/files/connectbox_home_button.conf`, included from the web-content location). It needs the `subs_filter` module (`libnginx-mod-http-subs-filter`; nginx-light has no `sub_filter`) and `include /etc/nginx/modules-enabled/*.conf;` in nginx.conf, which the template previously lacked. For a proxied backend such as kiwix-serve, set `proxy_set_header Accept-Encoding "";` so the upstream HTML is uncompressed, and use `location ^~ /kiwix/` - otherwise the vhost's `location ~ \.json$` regex takes `.json` requests away from the proxy.

## Interface translations

The app's UI strings (`<lang>/data/interface.json`) exist only in English upstream. mmiLoader writes each language's file from `/usr/local/connectbox/translations/<code>.json` (shipped from `ansible/roles/bootstrap/files/translations/`, reviewed: fa, ar, es, pt, zh-CN). For any other language it looks the strings up online (MyMemory) when the box has internet and saves them there; offline it falls back to English and retries next time. Each entry keeps the English it was translated from, so changed English is re-translated and hand corrections to `text` stick. Codes are normalised via languageCodes.json (`per`→`fa`, `ara`→`ar`): identical English name lists first, else the one 2-letter code sharing a name (`spa` "Castilian, Spanish"→`es` "Spanish"); the same mapping places multi-language ZIMs (Kiwix tags are 3-letter). Right-to-left languages get `"rtl": true` in languages.json. After a `saved.zip` restore, `refresh_interface_translations()` rewrites interface.json and the rtl flags. MyMemory output for short UI strings is often wrong (it is partly crowd translation memory) — review new languages before shipping them. mmiLoader is the only writer of interface.json (`apply_translations.py` was retired).

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
- **Admin session key is per box**: connectbox-manage signs admin login cookies with a random key it creates on first start in `/usr/local/connectbox/admin_session.key` (root, 600). Never put a fixed key back in the source (the old published key allowed forged admin logins), and keep the image-preparation task that deletes the file so image-made boxes don't share a key.
- **"Loading new content" page**: mmiLoader writes `/tmp/connectbox-indexing.html` during a full index only (`start_indexing_page`, progress via `indexing_progress`, removed before saved.zip is written, by atexit/SIGTERM/`--clear`; PxUSBm removes a leftover one at start if no mmiLoader runs). nginx (`connectbox_enhanced.conf.j2`) rewrites `/` and `/index.html` to it while it exists. Do not key it on `/tmp/creating_menus.txt` - that OLED message file is also written by the hat service's buttons. Web-content folders count as one item in the progress total. The message is shown in every language on the USB (`set_indexing_languages`, after `detect_language_dirs`) from the `INDEXING_TITLE`/`INDEXING_TEXT` interface strings (EXTRA_INTERFACE_STRINGS + shipped translations); progress is language-neutral "N / M". The page refreshes to `/?reload=<time>` and nginx sends `/` and `/index.html` with `Cache-Control: no-cache`: before that, browsers had heuristically cached the start page (2023 Last-Modified, no Cache-Control) for months, so a plain meta refresh showed the cached app and the menu never appeared by itself.
- **mmiLoader single-instance guard** is the marker file `/tmp/creating_menus.txt` (written by `initialize_run`, removed at the end of a run, by the SIGTERM handler and by `--clear`); mmiLoader exits at start if it exists. (Older docs said `/proc/*/cmdline` - that was never the code.)
- **saved.zip is written last**: `mmiLoader.py` checks `os.path.ismount("/media/usb0")` at each directory iteration and before writing `saved.zip`. If USB disconnects mid-run it exits cleanly without corrupting the content directory.
