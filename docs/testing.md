# Testing ConnectBox

How the ConnectBox code is tested, what has been tested so far, and what to run
for each change and each build. Built on 2026-11-01 from the Claude Code session
logs of 2026-10-04 to 2026-10-08, the Claude session of 2026-10-22 to 2026-10-30
and the fix log (`Hobby - ConnectBox\Claude\build-fixes-2026-10-22.md`, fixes 1–72;
records added through 2026-11-05).
Keep it up to date: add a line under "Test record" whenever a test is run, and a
row to the right table whenever a new test or harness is written.

## Where the tests are

| Place | What |
|---|---|
| `connectbox-pi/ansible/roles/bootstrap/files/test_mmiLoader.py` | mmiLoader suite (in the repo) |
| `connectbox-pi/ansible/roles/bootstrap/files/test_PxUSBm_mount.py` | PxUSBm USB mount simulation (in the repo) |
| `simple-offline-captive-portal/tests/test_captiveportal.py` | Captive portal suite (in the repo) |
| `connectbox-wifi-configurator/tests/` | `test_scan.py`, `test_wifi_configurator.py` (in the repo; not run in these sessions) |
| `connectbox-hat-service/tests/test_neo_batterylevelshutdown.py` | Hat-service suite (in the repo; not run in these sessions) |
| `connectbox-access-log-analyzer/lib/access_log_analyzer/tests/` | Log analyzer suite (not on the boxes; not run) |
| `connectbox-pi/tests/test_connectbox_static.py` | 27 checks against a **live box** over the network (not run in these sessions) |
| `connectbox-mediainterface/src/**/*.spec.ts`, `e2e/` | Angular unit and end-to-end tests of the media app (not run in these sessions) |
| `connectbox-pi/ansible/roles/bootstrap/files/test_RestartWLAN.py` | Not a unit test: it restarts the Wi-Fi on a real box |
| `connectbox-hat-service/tests/harness/` | Front-panel harnesses (fixes 21–51), `run_all.sh` |
| `connectbox-pi/tests/harness/` | PxUSBm and mmiLoader harnesses (fixes 35–53), `run_all.sh`; `phonehome64/` and `node22/` for a box |
| `connectbox-manage/tests/` | Setter, client Wi-Fi, setBrand, body-parser and admin-login harnesses (fixes 26, 48, 61–66) |
| `connectbox-admin-ui/tests/` | Cloud-items visibility (fix 55) |
| `Hobby - ConnectBox\Claude\hatbox\` | Earlier versions of the harnesses, the portal language test, the screenshot script |

The harnesses each take the file(s) under test as arguments, so they can
be pointed at the repository copy, a copy fetched from a box, or an older version
(to prove the test fails on the old code).

## General rules (learned the hard way)

1. **Prove a new test can fail.** Run it against the old code too; it must fail
   there (done for test_PxUSBm_mount, test53, test_clientwifi, test_setbrand,
   fscheck_test, movemount_test, test47, isconnected).
2. **Copy files to a box from git, never from the Windows working tree**
   (`git show HEAD:path`, or strip CR). A CRLF `#!/usr/bin/python3` line broke
   `connectboxmanage` on .153 (fix 64 log).
3. **Back up before installing on a box** (`/root/backup-fixNN/`) and note the
   backup in the fix log.
4. **Ask before restarting a service** while Kirk may be using the front panel, and
   **never install or restart during a USB copy or an index**
   (`/tmp/creating_menus.txt`, `/tmp/connectbox-usbcheck.txt`, `pgrep mmiLoader`).
5. **A PxUSBm restart can change the box's IP** (it resets the Wi-Fi). Find the box
   again by its wired MAC: `for i in $(seq 1 254); do ping -c1 -W1 192.168.1.$i & done; wait; ip neigh | grep <mac>`.
6. **Tests that talk to a cloud server must not mark real logs as sent.**
   `connectboxmanage get syncweblog` appends `{"sync":true,...}` to
   `/var/log/connectbox/connectbox_enhanced.json`; remove that line after a test.
7. **Look beyond the changed program.** Fix 60 (Node 22) passed its own tests but
   broke PxUSBm, which called `/usr/bin/pm2` by full path (fix 60b). After any
   change to a shared program or path, grep all repos for it and check
   `systemctl show PxUSBm -p NRestarts` and the Wi-Fi after a reboot.
8. **Browser tests need a clean browser:** an Incognito window (no saved language,
   no cached pages); on Kirk's PC `connectbox` comes from the Windows hosts file,
   which must follow the box's IP. From Rpi-Build or a script, send
   `Host: connectbox` (nginx serves the captive-portal page for a bare IP).

## 1. Automated suites (run before every commit that touches the code)

| Suite | Covers | How to run | Last result |
|---|---|---|---|
| `test_mmiLoader.py` | mmiLoader: folder types, collections, icons, thumbnails' selection, translations and phone language codes, ZIM (single and multi-language, TED), Word/.doc, Excel/.xls, PowerPoint/.ppt, permissions fix, duplicate names, own content, progress text, default language, saved.zip refresh | `cd connectbox-pi/ansible/roles/bootstrap/files && python3 test_mmiLoader.py` (needs `mammoth openpyxl xlrd xlwt olefile python-pptx`; without mammoth S17 fails) | 301/301 (2026-10-28, fix 48c) |
| `test_PxUSBm_mount.py` | PxUSBm.mountCheck(): mount/unmount, partitioned and whole-disk keys, ext4/FAT/NTFS options, loader start/stop, removal clean-up, Kiwix library clearing | `cd connectbox-pi/ansible/roles/bootstrap/files && python3 test_PxUSBm_mount.py` | 32/32 (2026-10-29, fix 53) |
| `test_captiveportal.py` | Captive portal answers per phone family, page language | start the portal locally on 127.0.0.1:5000 (the tests send HTTP requests to it, see its README), then `cd simple-offline-captive-portal && make test` (`python -m unittest discover -s tests`). Page-language checks used the Flask test client with the translation files in `Claude\hatbox\portal-test` | 20 passed, 1 skipped (2026-10-26, fix 31) |
| wifi-configurator `tests/` | Channel scan and config writing | `cd connectbox-wifi-configurator && python3 -m pytest tests` (check its README/tox.ini first) | **Not run yet** |
| hat-service `tests/` | Battery/shutdown logic | `cd connectbox-hat-service && python3 -m pytest tests` (check its README first) | **Not run yet** |
| `test_connectbox_static.py` | A built box over the network: portal, DNS, web, admin API | `TEST_IP=<box ip> python3 -m unittest tests/test_connectbox_static.py` (needs `requests dnspython`). **Not run yet** – it logs in with the default `admin`/`connectbox` and predates the short admin sessions (fixes 26–28), so review it before relying on it; a good candidate for the release-image check |
| Ansible syntax | Playbook loads | on Rpi-Build: `cd connectbox-pi/ansible && ansible-playbook --syntax-check site.yml`; YAML: `python3 -c "import yaml;yaml.safe_load(open('roles/<role>/tasks/main.yml'))"` | OK 2026-10-30 (build ran) |
| Script syntax | Changed scripts | `bash -n x.sh`, `sh -n x.sh`, `python3 -m py_compile x.py`, `node --check x.js` | run with each fix |

## 2. Test harnesses in the repositories (run when the program they cover changes)

The harnesses written for fixes 21–66 are in the repository of the code they test. Each folder has a
README with the details; the `run_all.sh` scripts run every harness in that folder against the
checkout and end with `ALL PASSED` or `SOME TESTS FAILED`. Linux only (they read `/proc`).
Each harness takes the file(s) under test as arguments, so it can also be pointed at a copy fetched
from a box or at an older version (to prove the test fails on the old code).

| Where | Run | Harnesses (what they cover) | Last result |
|---|---|---|---|
| `connectbox-hat-service/tests/harness/` | `bash tests/harness/run_all.sh [connectbox-pi]` – tests the **deployed** set: this repo's package with connectbox-pi's `displays.py` and `page_display_image.py` copied over it, as the build does | `sim43.py` (admin commands, copy/erase, error pages, progress, button timing), `unit35c.py` (brand.j2 atomic write/read, status file), `usb_test.py` (isUsbPresent), `fscheck_test.py` (file-system check by type), `movemount_test.py` (moveMount), `test51_hats.py` ("Checking USB" on the panel) | 84, 23, 10, 8, 4, 9 – all pass (2026-11-01) |
| `connectbox-pi/tests/harness/` | `bash tests/harness/run_all.sh [connectbox-hat-service]` – copies the files to neutral names (some tests look for processes named `mmiLoader.py`) and takes the pre-fix code (d1913b5) from git, or from `OLD_DIR` | `px35.py` (mount slot booking), `test38.py` (stale status file, SIGTERM), `testwc.py` (`.webcompress`), `test47.py` (default language), `test_make_zip.py`, `test_px_status.py` (start-up status file), `test51_px.py` (FAT dirty check; needs dosfstools), `test53.py` (dead/stacked mounts) | 5, 19, 7, 9, 8, 4, 21, 11 – all pass (2026-11-01) |
| `connectbox-pi/tests/harness/phonehome64/` | on a box as root, see its README; afterwards remove the `{"sync":true}` line it adds (rule 6) | phonehome.py end to end as www-data against `mock_cloud.py` with a bind-mounted test brand.j2 | key made, 4 requests with `Bearer <Box ID>\|<key>` (fix 64) |
| `connectbox-pi/tests/harness/node22/` | on a box as root, in order: fetch, test, switch, after | moving an existing box from Node 16 to Node 22 by hand (new builds install Node 22); `node22_test.sh` compares 24 read-only `get.*` answers and a second server on port 5012 | identical except wifistatus counters (fix 60) |
| `connectbox-manage/tests/` | `npm ci`, then `bash tests/run_all.sh` | `test_clientwifi.js` (first network block only, scan_ssid kept), `test_setbrand.js` (number rule, `=`, phone, security key without wget), `bp_test.js` (body-parser) | 10, 11, 4 – all pass (2026-11-01) |
| `connectbox-manage/tests/` (container only, root) | see the README | `cbm_test.js` + `fake_sudo.sh` (setters: old sed vs new Node, injection, refused values, exact arguments; needs 44a66bf), `admin_login/` (password checks and login session in Playwright Chromium) | 62/62; 30/30 (2026-11-01) |
| `connectbox-admin-ui/tests/` | `bash tests/run.sh` | `test_cloudpackage.mjs` (Sync / Subscribe / Download Missing shown only with a Box ID and a saved Cloud Server URL) | 8/8 (2026-11-01) |

`Hobby - ConnectBox\Claude\hatbox\` still holds the earlier versions of these harnesses, the portal
language test (`portal-test`) and `spec_shots/shoot.py` (not a test: phone-size screenshots via headless
Chromium; Rpi-Build's Chromium currently fails with a zygote error).

Patch scripts for the released apps (`connectbox-pi/ansible/roles/enhanced-content/files/patch_*.py`,
and the inline 3.js/6.js patch tasks) are tested the same way each time:
run against the **real current release bundle** – patched once, unchanged on a
second run, `node --check` passes, an unknown bundle exits with an error, and
for patch_admin_login a release that already contains the change is reported
"built into this release". Re-run these after every new connectbox-mediainterface
or connectbox-admin-ui release.

## 3. Checks on a test box after installing a change

Find the box (OLED or `ip neigh`), back up, install, then:

| Area | Check |
|---|---|
| Services | `systemctl --failed`; `systemctl is-active hostapd dnsmasq PxUSBm nginx captiveportal neo-battery-shutdown pm2-root`; `systemctl show PxUSBm -p NRestarts` stays 0 |
| connectbox-manage | `/usr/bin/pm2 status` shows `index` online; `connectboxmanage get boxid`, `get hostname`; `curl -H "Host: connectbox" http://127.0.0.1/admin/api/ismoodle` → 200; protected calls without login → 401 |
| Node | `node --version` = v22.x; `ls -l /usr/bin/pm2` points to `/usr/local/bin/pm2` |
| Box ID | `cat /sys/class/net/eth0/address` = the fixed MAC (02:…) before and after a reboot; journal `fixed_eth_mac: eth0: MAC set to …` |
| Wi-Fi | `iw dev`: AP (type AP, SSID "Connectbox - Free Media") on the RTL88xx adapter; client joined (`iw dev wlanX link`); no "recursion detected" in `journalctl -b`; at most two Wi-Fi adapters plugged in |
| Phone-home | `/tmp/push_messages.log` after the next 10-minute run: no traceback ("FATAL: No server_url" is the normal stop without a cloud server) |
| USB insert | key mounted at /media/usb0, "Checking USB" only for a dirty FAT key (≤ 2 min), loading page and OLED %, menus appear, `saved.zip` written last |
| USB removal | menus cleared (or the box's own content re-indexed), Kiwix library emptied, mount gone |
| Logs | no repeated errors in `journalctl -u PxUSBm`, `pm2 logs index --err`, `/var/log/PxUSSBm.log` (two S) |

## 4. Functional tests by hand (phone or browser)

Run the relevant rows after a change in that area, and all of them on a release image.

| Area | Test | Last done |
|---|---|---|
| USB file systems | FAT32, exFAT, NTFS, ext4 partitioned, ext4 whole disk (`wipefs -a; mkfs.ext4 /dev/sdX`), each mounts and indexes; ext4 with private files (`chmod 600`/`700`) opens after the permission fix | ext4 whole-disk 2026-10-06; private files 2026-10-06; FAT/NTFS/exFAT Oct 26–29 |
| USB re-insert | second insert restores from saved.zip in seconds; a key swapped without reboot re-indexes | 2026-10-05 |
| Dirty FAT key | key from another box shows "Checking USB", mounts within 2 min | 2026-10-29 (.153) |
| Own content | front panel Copy from USB → box shows its own content; plug a key → key content; pull it → own content again | copy 2026-10-26/27; plug/pull by hand still open (fix 29) |
| Front panel | copy to/from USB with progress, "Not enough room", "File over 4GB" on FAT, error page stays lit, key left unmounted after a failed copy, both buttons 4 s, one button 4 s = shutdown | 2026-10-27 (.200) |
| Content types | Word/.doc, Excel/.xls, PowerPoint/.ppt as pages; PDF with a same-named .doc opens the PDF; download button shows the size; ZIM cards open in Kiwix with the home button; TED opens in the menu language | Oct 5–7, Oct 24 |
| View counting | tap a web/ZIM card → a line in `/var/log/connectbox/connectbox_enhanced.json` | 2026-10-05 |
| Broken links | a dead link inside web content returns to the item's start page | 2026-10-05 |
| Languages | Incognito with Portuguese/Spanish/Arabic first → menus start in it (Arabic right-to-left); French → default; a language picked from the button wins after reload; key with only `eng` → English default | 2026-10-06, 2026-10-28 |
| Loading page | during a full index the page shows progress in the phone's language and switches to the menu by itself | 2026-10-07, 2026-10-26 (headless) |
| Captive portal | joining phone opens the portal page in its language; Android 10+ "Use this network as is" hint; old iOS/Android checks still answered | 2026-10-26 (Android UA), S25 adb logcat 2026-10-23 |
| Admin login | Configuration always asks for the password; Exit → main screen and logged out; Back/another link/closing tab logs out; 5 min idle → password again; login page shows no default password; wrong password 401; password with shell characters works | 2026-10-26 (headless 14/14 + 16/16) |
| Admin pages | Delete Stats last in Usage Reports; Sync/Subscribe/Download Missing only with Box ID + URL; settings save (SSID, channel, passphrase, client Wi-Fi, hostname, cloud fields incl. a key starting with digits) | layout 2026-10-29; **Kirk's login + settings test under Node 22 still open** |
| Old phones | menus, portal and ZIM pages on iOS 9 / Android 4–5 era browsers | ZIMs on Kirk's phone 2026-10-05; very old phones not recently |

## 5. Every build (`make_cb.py`)

1. Before: every repository committed **and pushed** (the build clones connectbox-pi
   and pulls connectbox-manage, the captive portal, wifi-configurator and the admin-ui
   release from GitHub); on Rpi-Build `git -C ~/connectbox/connectbox-tools pull`;
   use `--update_ansible Y` (branch `master`) so connectbox-pi is cloned fresh –
   with N it reuses whatever old copy is in `deployment/connectbox-pi`.
2. Target: a fresh Armbian 23.02.2 card, root key installed, **one or two** Wi-Fi
   adapters.
3. Watch the log (`~/build-<date>.log`): `grep -c '^TASK'`, `grep -E '^fatal|FAILED!'`.
4. Pass criteria: `PLAY RECAP … failed=0 unreachable=0`. Expected ignored errors
   (2026-10-30: 3): network-interfaces "Check for drivers that already exist…" ×2
   (no `<kernel>/` driver folder) and wifi-ap "Reload hostapd -- Allow ignore errors
   for devices without WLAN" (interface names change only at the next boot). Any
   other ignored error is new and must be looked at.
5. Confirm the important tasks ran: kernel/dtb/u-boot/armbian-*/base-files hold and
   the after-upgrade assert; phonehome.py and ConnectBoxManage.sh (brand.j2
   versions); fixed_eth_mac.sh and its udev rule; Node.js download with SHA-256 check,
   "Check that the expected Node.js version" passed, pm2 install, /usr/bin links;
   image-preparation and "Perform final shutdown".
6. Do not boot the build card again before imaging.

Build history: 2026-10-23 ok (after fixes 1–11), 2026-10-24 ok (24 ignored),
2026-10-28 two runs (resume needed; fix 45), 2026-10-28b ok (10 ignored),
2026-10-30 ok (failed=0, 3 ignored, connectbox-pi 580ffa3, tag v20261030).

Raspberry Pi OS Trixie (CM4): build with `python3 make_cb-rpi.py` (ansible-core
2.17.14 in its own venv; `--setup` once), after `setup_raspbian_host.sh <ip> <user>`.
Expect one reboot during the build.  First test build history: 2026-11-04, 12 runs
to failed=0 (fix 67).

## 6. Every image

1. Shrink on Rpi-Build with `shrink-image.sh` (no .sha256); check `e2fsck -fn` on the
   image is clean and the partition table is as expected.
2. Flash to a **different** card and boot:
   - first boot expands the file system in up to 3 short boots, with no
     "A stop job is running for ifup…" wait (fix 50);
   - Wi-Fi names wlan0/wlan1, AP up on the RTL88xx adapter, captive portal and menus;
   - SSH off (enable with `.connectbox/enable-ssh` on a key to inspect);
   - Box ID shown and unchanged after a reboot; **two boxes from the same image show
     different Box IDs**;
   - `node --version` v22, `/usr/bin/pm2 status` online, PxUSBm NRestarts 0;
   - a USB key indexes; Section 3 and the release rows of Section 4.

## 7. Not tested yet / to add

- The 2026-10-30 image (not made yet) and its first boot.
- Kirk's admin login and settings changes under Node 22 in a browser.
- Own content: plug a key in and pull it out by hand (fix 29).
- Client Wi-Fi (`ifup@wlan1`) failing once at boot right after DHCP (2026-10-29 15:48) – cause unknown.
- Three or more Wi-Fi adapters (PxUSBm leaves them alone; AP can end up on an MT7601U).
- `test_connectbox_static.py` (live box) and the mediainterface spec tests.
- wifi-configurator suite: 12 of 29 fail (2026-11-04; was 14 on 2026-11-01). The country-block bug below was fixed on 2026-11-04 (fix 67: `scan.py` matches the `country XX:` header only); the remaining failures are out-of-date tests. Earlier note: Most tests are out of date (old function signatures, `range` instead of a list), but they also show a real bug: `scan.get_country_rules_block` matches the country code anywhere in a line (`AU` in `AUTO-BW`, `IR` in `NO-IR`, `JP` in `DFS-JP`), so with the test regulatory database AU, NO, IR, TD, DM and DO get no channels (hostapd then gets `channel=0`), SE and ET get 1–11, JP gets another country's list (fixed 2026-11-04, see above).
- hat-service repository suite: only a placeholder test (`assertTrue(True)`); the real front-panel tests are in `tests/harness/`.
- connectbox-manage `admin_login/` with a current admin-ui build (run on 2026-11-01 with the 26 Oct build).
- Orange Pi Zero 2, Radxa CM3 and Raspberry Pi boards other than the CM4 on current
  OS releases (the CM4 on Raspberry Pi OS Trixie and the NanoPi NEO on Armbian 23.02
  are tested).
- A fresh CM4 build with `make_cb-rpi.py` after the 2026-11-04/05 fixes (fixes 67-72),
  and a NanoPi NEO build with them (firewall role, interfaces template without the
  `hostapd` line, internet sharing, remembered WiFi, wifi-configurator single start).
- Auto-connect to a remembered client WiFi network when the saved one is out of range
  (only one network, Wilson1, was available).
- Internet sharing through the client WiFi alone (Ethernet unplugged), and a metered
  phone hotspot as the uplink.
- With the Ethernet cable out, the CM4 did not answer on its client WiFi address
  either (2026-11-05 10:35) - cause not found.
- 8812au driver reload: hostapd came up "ENABLED" with a dead radio once after
  `modprobe -r/modprobe` (2026-11-05, before the interfaces fix) - not retried since.
- Central server (connectbox-chathost) build on a real Ubuntu 24.04 server, and
  phone-home against it (only the mock server so far).
- Native-speaker check of the shipped translations.
- Very old phones (iOS 9 / Android 4–5) against the current menus.

## Test record

Most recent first. One line per test run: date, what, result, where it is described.

| Date | Test | Result | Reference |
|---|---|---|---|
| 2026-11-13 | HDMI section: visitor "Play on HDMI" as a toggle switch, language labels bold (Kirk). hdmi_test.py 54/54 (+2: toggle markup, save after click with the old checkbox still handled); admin-ui yarn build (Node 16), five admin patch scripts report built in; headless Chromium with made-up box data: switch shows on for visitor_play 1, each click flips it and saves hdmi_visitor_play=0 then =1; toggle inside the card. Installed on the CM5 (.36, backup /root/backup-20261113f) | pass; Kirk's look in the browser still to do | fix 86 |
| 2026-11-13 | HDMI playlist chooser shows the language (Kirk): groups "Language: xxx", playlist entries "name (kind) · Language: " + underlined language; About text changed (admin-ui 0f026c7). tests/harness/hdmi_test.py +2 checks (embedded script == admin-ui hdmi_admin.js still checked); admin-ui yarn build (Node 16) with all changes, five admin patch scripts report built in; installed on the CM5 (.36, backup /root/backup-20261113d) | hdmi_test 51/51; look in the browser by Kirk still to do | fix 85 |
| 2026-11-13 | Internet Data page follows internet sharing (fix 85b, Kirk): switch off by default, on with sharing, off again with sharing unless set by hand. connectbox-manage tests/test_setbrand.js 28/28 (17 switch checks: missing key follows sharing; sharing on -> 1 + auto mark; off -> 0; admin on by hand survives sharing on/off; admin off while sharing on stays off); hat-service run_all ALL PASSED (internet_switch_test 19: page shown exactly while the switch is on, older globals.py falls back to wanted(), brand.j2 without the key follows internet_sharing in any letter case); image-preparation regex sets lcd_pages_internet and _auto to 0; admin-ui yarn build (Node 16), all five admin patch scripts report built in. Installed on the CM5 (.36, backups /root/backup-20261113b): hat service and connectbox-manage running, switch reads 0 (brand.j2 sharing 1, switch 0 from Kirk's earlier test) | pass; the automatic on/off not yet tried in the browser | fix 85 |
| 2026-11-13 | LCD page switches (fix 85) on the CM5 made from the 2026-11-12 image (.36): new displays.py/globals.py, connectbox-manage functions.js and admin page build installed by hand (backups in /root/backup-20261113); admin page lists both switches, missing keys read 1 (getBrand and hat-service globals); switches tested by Kirk in the browser and on the OLED | pass (Kirk, 08:31) | fix 85 |
| 2026-11-13 | Admin switches for the front panel's IP addresses and Internet data pages (fix 85; done from GitHub copies while the link to Kirk's PC was down): hat-service tests/harness/run_all.sh with the new internet_switch_test.py (switch 1/"1"/missing -> shown when wanted, 0/"0"/"false" -> hidden; fails 3 checks on the old displays.py); connectbox-manage tests/test_setbrand.js +7 checks (missing lcd_pages_network/lcd_pages_internet read 1, saved values read back); admin-ui yarn build (Node 16) and pug render: both switches in LCD Interface between Stats and Admin; brand_txt.j2 rendered with group_vars -> valid JSON with both keys 1; test_PxUSBm_mount.py 32/32 | run_all ALL PASSED (12 new), test_setbrand 18/18; not tried on a box or in a browser yet | fix 85 |
| 2026-11-12 | Swap file size check (hat-service role, fix 84): first steps run from RPi-Build against the CM5 (.55): no /swapfile -> 0 bytes; the grow/fill condition with connectbox_os=armbian at 0, 50 MiB, 400 MiB - 1 byte -> grow, at 400 MiB and 1 GiB -> no grow | pass; the swap steps themselves (fallocate, dd, mkswap, swapon) not run - first real run on a NEO build | fix 84 |
| 2026-11-12 | /tmp size (hat-service role, fix 83): the new /tmp steps run alone from RPi-Build against the CM5 (.55, 8 GB, no /tmp line in fstab): as a Pi -> tmp.mount drop-in size=25%, /tmp 2.0G; second run rewrites nothing; made to look like a NEO -> drop-in size=256M, /tmp 256M, then back to 2.0G; neither a Pi nor a NEO -> every /tmp step skipped | pass; the /etc/fstab path (Armbian), a real NEO and a reboot not tried yet | fix 83 |
| 2026-11-11 | kiwix-tools download backstop (kiwix role run alone against the CM5): dead first source then mirror; only a dead source with the archive in the build machine's cache; already installed (nothing fetched); source throttled to 50 KB/s given up after the time limit, alone (build stops with the message naming the cache folder) and followed by a mirror (installs). kiwix-serve active, /kiwix/ 200 afterwards. Not yet run inside a full build; armv6 (NEO) path not run | pass | CM5 at 192.168.1.54 |
| 2026-11-11 | Node 22 on Raspberry Pi OS (CM5, Trixie, arm64): fresh build had Debian's Node 20.19.2; the changed enhanced-content steps run by hand on the box (purge apt nodejs/npm, nodejs.org v22.23.4 tarball with SHA-256 check, /usr/bin links): node v22.23.4, npm 10.9.9, pm2 7.1.2, connectbox-manage online on 22.23.4, HDMI status API answers, no failed units. Not yet run as a full Ansible build | pass | CM5 at 192.168.1.54 |
| 2026-11-11 | HDMI screen (fix 81): connectbox-pi tests/harness/hdmi_test.py (player path checks, playlist, HDMI port, play / back to playlist / splash with a fake mpv, splash picture, both page patches) | 39/39; run_all.sh all pass | fix 81 |
| 2026-11-11 | HDMI screen: connectbox-manage tests/test_hdmi.js (web paths, media list, playlist, visitor switch, admin play, player reload; fake player socket) | 30/30; run_all.sh all pass | fix 81 |
| 2026-11-11 | HDMI "Play playlist" button: hdmi_test.py on a Windows PC (3 new checks: button in the section, script adds it to an already patched page, section equals the admin-ui copy) | 34 pass, 8 fail; the 8 are Windows-only (no `os.chown`, `/` in the test's expected paths) - re-run on Linux; not tried on a box | fix 81 |
| 2026-11-11 | HDMI: videos played with sound behind the splash (global `--cover-art-files`). Fixed player copied to the CM5 box: Play now on a .3gp -> mpv video track H.263 176x144 (before: PNG 1920x1080); Play now on an mp3 -> splash picture; stop -> playlist video; no mpv errors logged. hdmi_test.py +4 checks (Windows run, same 8 Windows-only failures) | pass on the box (mpv's report; picture on the monitor confirmed by Kirk) | fix 81 |
| 2026-11-11 | HDMI Stop really stops (it went back to the playlist, so the screen could not be stopped): hdmi_test.py on the build Pi (Linux), +3 checks (stop -> splash, mode stopped; a chosen file then the splash again; reload -> playlist). On the CM5 box: stop -> stopped, reload -> splash (its playlist was empty), no errors | 48/48 on Linux; with a filled playlist not tried on the box | fix 81 |
| 2026-11-11 | Host name change applied at once (connectbox-manage `set.hostname`: `hostname <name>` + /etc/hosts via `hostsWithName`; before, only /etc/hostname, brand.j2 and nginx were written): connectbox-manage tests/test_hostname.js on the CM5 box; then `connectboxmanage set hostname MORTON` there | 13/13; running name, /etc/hostname, /etc/hosts (127.0.1.1, 127.0.0.1, learn.<name>, 10.129.0.1) and nginx server_name all MORTON, `getent hosts MORTON` answers, no reboot. Open: `connectboxmanage set hostname 'Morton Box'` ends in a clientcli IndexError instead of the refusal text | - |
| 2026-11-11 | Front panel "IP addresses" page (hat-service page_network.py): hat-service tests/harness/run_all.sh on the build Pi (new network_page_test.py: wificonf names, own address not the wlanX:0 alias, rows fit 20 characters, page order and screen_enable counts). Files copied to the CM5 box, service restarted | run_all ALL PASSED (181 checks, 18 new); on the box the page's rows read AP 10.129.0.1, WiFi 192.168.1.20, Eth 192.168.1.31 and the service runs with the OLED; the picture on the OLED to be confirmed by Kirk | - |
| 2026-11-11 | HDMI screen on the CM5 (.31, 1920x1080 monitor on HDMI-A-1): mpv 0.40 on DRM without a desktop; splash 8 s, H.264/AAC video with HDMI sound; player loop of clip / picture / tone; play interrupts and returns at eof; /etc/passwd in the playlist and /etc/shadow as a play request refused; hdmi-screen role run from RPi-Build (ok=10 changed=4 failed=0), service enabled; public status/play through nginx (play refused while visitor play is off); both page patches applied, idempotent, bundles pass node --check | pass on the box; what the monitor shows and the phone buttons still to be confirmed by Kirk | fix 81 |
| 2026-11-11 | `| bool` on do_image_preparation / developer_mode / enhanced_interface / shutdown_in_image_preparation conditions (fix 80): ansible-playbook --syntax-check site.yml (ansible-core 2.17.14 on RPi-Build); test play with `-e developer_mode=false -e do_image_preparation=False` -> sshd disabled, no image preparation, dnsmasq not in developer mode; `=true`/`=True` -> the opposite; JSON booleans same as plain | pass | fix 80 |
| 2026-11-11 | hat-service nopanel_test.py (fix 79): Pi/CM with no AXP209 gets DummyHAT, LED helpers and DummyDisplay calls are no-ops, DummyHAT exits for a restart when the AXP209 answers again; old files 6/12 | 12/12; run_all.sh all pass (84, 23, 10, 8, 4, 9, 13, 12). On the CM5 (.29): q4y2018HAT detected as before; a stuck bus during running crashed the service once, ExecStartPre recovery freed it (9 pulses) and the restart came back | fix 79 |
| 2026-11-10 | i2c_bus_recover.sh on the CM5 (.29): free bus no-op (0.27 s); --force; real stuck bus released after 9 pulses | pass; not tested on a CM4 | fix 78 |
| 2026-11-09 | hat-service shutdown_test.py (fix 75): failed power-off tries shutdown -h now, then "Shutdown failed" page and buttons back; old hats.py fails 11/13 (frozen) | 13/13; run_all.sh all pass (84, 23, 10, 8, 4, 9, 13) after adding page_internet to sim43's fakes | fix 75 |
| 2026-11-09 | Power-off script on the CM4 (.29) run by hand | box powered off (Kirk); button press with the script not yet tested | fix 75 |
| 2026-11-06 | wifi-configurator channel choice: 14 scenario checks and the 6 changed/new test_scan.py functions with the box's venv Python; on the box channel 6 kept on every AP restart | pass | fix 74 |
| 2026-11-05 | ATtiny probe for the multi-battery page default on the CM4 (bus 10: 0x14 answers, 0x15 does not) | pass | fix 72 |
| 2026-11-05 | Amber LED with hostapd stopped for 60 s (PxUSBm paused) | LED off, then on again (Kirk) | fix 71 |
| 2026-11-05 | AP "ENABLED" with a dead radio: ifdown/ifup wlan1 with and without the interfaces `hostapd` line; reboot | dead 2/2 with the line, 0/2 without; after the 11:46 reboot hostapd started once, no restart needed | fix 71 |
| 2026-11-05 | Three CM4 reboots: hostapd start count, channel scan, radio state, wlan0 recovery, sharing after reboot | boot scan works, single start; dead radio caught and restarted by PxUSBm; wlan0 recovered; sharing after reboot fixed (wlan1:0 address), Kirk: internet, wi.fi, connectbox work | fix 70 |
| 2026-11-05 | Beacon watch from the box's own client (iw scan every 5-9 s) on channels 9, 5, 4 | gaps of 10-27 s while the radio was dead; steady on channel 9 once it was set up | fix 70 |
| 2026-11-05 | Internet sharing on the CM4 with Kirk's phone: on/off from the admin page, internet, wi.fi, gowifi.org, connectbox; DNS answers from the box; dnsmasq.conf restored byte for byte; reboot with sharing on | pass | fixes 69, 70 |
| 2026-11-05 | Data counter (usage_test.py, offline) 9/9; on the box 5.4 MB down / 0.4 MB up after a reset; front-panel Internet page, admin total, Advanced kept after re-login | pass (Kirk) | fix 69 |
| 2026-11-05 | Firewall role alone on the CM4 (fwtest.yml on Rpi-Build): iptables-nft, rules loaded and saved, second run unchanged; rules loaded at boot | pass | fix 69 |
| 2026-11-05 | Remembered client WiFi: test_kw.py (offline) 18/18; on the CM4 Wilson1 learned, internet test through wlan0 (separate routing table) | pass | fix 68 |
| 2026-11-05 | eth0 lost lease re-created (dhclient killed, IPv4 flushed) | old check_eth0 did nothing; new one restored eth0 in 85 s | fix 68 |
| 2026-11-05 | Wipe client WiFi: connectbox-manage function on temp files (node); patch_admin_clientwifi_wipe/internet_sharing/advanced on the release bundles (idempotent, `node --check`) | pass | fixes 68, 69 |
| 2026-11-04 | CM4 Lite on Raspberry Pi OS Trixie: test builds until failed=0 (12 runs), then boot-by-boot fixes; USB soak on DWC2 vs XHCI | failed=0; 0 RTL8812AU drops in 13 h on DWC2 (12 in 85 min on XHCI) | fix 67 |
| 2026-11-04 | wifi-configurator suite after the country-block fix | 12 failed (out-of-date tests) instead of 14 | fix 67 |
| 2026-11-01 | wifi-configurator `pytest` (Python 3.10, copy of the repo); hat-service `pytest tests` | wifi-configurator 11 passed, 14 failed, 4 skipped (country-block bug, see section 7); hat-service 1 passed (placeholder) | section 7 |
| 2026-11-01 | Harnesses moved into the repositories; `run_all.sh` for hat-service and connectbox-pi and admin-ui run on the real checkouts; connectbox-manage in a test container | all pass: hat-service 138, connectbox-pi 84, connectbox-manage 25 + cbm_test 62 + admin_login 30, admin-ui 8; test_PxUSBm_mount 32/32, test_mmiLoader 317/317 | `tests/harness/README.md` in each repo |
| 2026-10-30 | Build on fresh card (.153) | failed=0, 3 expected ignores | fix log "Build 2026-10-30" |
| 2026-10-29 | test_setbrand.js on .156 | 11/11 (old 6/11) | fix 66 |
| 2026-10-29 | /usr/bin links task against .156 + `/usr/bin/pm2 status` | ok=4 failed=0 | fix 60b |
| 2026-10-29 | wifi_configurator run_by_ifupdown_for 5 cases; reboot: no "recursion detected" | pass | fix 65 |
| 2026-10-29 | phonehome64 mock-server run on .153; 18:00 cron run | pass | fix 64 |
| 2026-10-29 | fixed eth0 MAC: computed twice, dry run, udevadm test, reboot | pass | fix 63 |
| 2026-10-29 | isconnected old/new with reachable and unreachable host | new correct | fix 62 |
| 2026-10-29 | test_clientwifi.js | 10/10 (old 5/10) | fix 61 |
| 2026-10-29 | Node 22 side by side on .153; switch; reboot (pm2-root start) | pass; PxUSBm regression found later (60b) | fix 60 |
| 2026-10-29 | cpt/test.mjs, test2, test3 (admin cloud items) | 10/10, 9/9, 8/8 | fix 55 |
| 2026-10-29 | Admin-ui build like the release job | only index.html differs | fix 54 |
| 2026-10-29 | test53, test51_px, test51_hats, test_PxUSBm_mount | 11/11, 21/21, 9/9, 32/32 | fixes 51–53 |
| 2026-10-29 | Expansion reboots on .153 (fix 50) | no stop-job wait | fix 50 |
| 2026-10-28 | test_mmiLoader 301/301, test_PxUSBm_mount 32/32, test_make_zip 8/8, test_px_status 4/4, cbm_test.js 62/62 | pass | fix 48 |
| 2026-10-28 | test47 | 9/9 | fix 47 |
| 2026-10-28 | shrink-image.sh condition, `bash -n` | pass | fix 46 |
| 2026-10-28 | Test play on Rpi-Build for build fixes; TestPxUSBm marker; patch_admin_login on the release | pass | fix 45 |
| 2026-10-27 | sim43 84/84 ×3, unit35c 23/23, usb_test 10/10; on .200 "File over 4GB" path | pass | fix 44 |
| 2026-10-27 | movemount_test 4/4, fscheck_test 8/8, sim41 76/76 | pass | fixes 42–43 |
| 2026-10-27 | testwc 7/7, test38 19/19 | pass | fixes 38–40 |
| 2026-10-26 | sim_test 72/72, unit35 23/23, px35 5/5, usb_test 10/10 | pass | fixes 35–37 |
| 2026-10-26 | Ansible syntax-check; image leftovers tasks on a scratch folder; `--check` on .176 | pass | fix 33 |
| 2026-10-26 | Translations: 41/41 file checks; S22; 50 languages on .176; portal languages | pass | fix 32 |
| 2026-10-26 | Portal repo tests 20 + 1 skipped; Flask client 24 checks; .176 with Android UA | pass | fix 31 |
| 2026-10-26 | Headless Chromium: loading page languages 9/9 | pass | fix 30 |
| 2026-10-26 | check_internal_content 9/9; own content re-index on .176 | pass | fix 29 |
| 2026-10-26 | Login injection and password checks 16/16; session checks 14/14; admin Exit 7/7 | pass | fixes 26–28 |
| 2026-10-25/26 | sim_test 45→56/56, usb_test 10/10, test_mmiLoader 302 (+S15 stale) | pass | fixes 21–25 |
| 2026-10-24 | .doc/.ppt converter on the Apache POI corpus (145 .ppt, 159 .doc), Kirk's files; S21 | no crashes; 294 pass + S15 stale | fix 19 |
| 2026-10-24 | 3.js slug patch on copies; PDF opens in Chrome on .176 | pass | fix 18 |
| 2026-10-23 | Builds and image test boot (fixes 1–17) | see fix log "Build log" | fixes 1–17 |
| 2026-10-07 | mmiLoader 200→264 checks; Word/Excel/PowerPoint pages on the box in Chrome; loading page live during a re-index; download sizes | pass | session ef390161 |
| 2026-10-06 | Session-key fix: forged cookie 200 → 401, real login, key survives restart; chathost `npm ci` smoke test; make_cb.py/prepare_release.py with mocked prompts | pass | session ef390161 |
| 2026-10-06 | No-partition ext4 key; one ZIM under several languages; spa→es; TED language; kiwix-serve restart check; private-file permission fix; browser language in Incognito | pass | session ef390161 |
| 2026-10-05 | ZIM proof of concept on the NEO (0.08 s pages, 0.8–1.3 s search, 59 MB); ZIM cards, home button, phone test | pass | session 029e1081 |
| 2026-10-05 | test_PxUSBm_mount created (29, old code fails 15), loader `--wait` bug found; ext4 partitioned key; nginx broken-link redirect (12 checks on nginx for Windows, then on the box); web content view counting tap test | pass | session 029e1081 |
| 2026-10-04 | 6.js view-count patch against the real release (stock and old-patched), idempotent, `node --check`; mmiLoader refactor 61/61 | pass | session 029e1081 |
