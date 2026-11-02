# Testing ConnectBox

How the ConnectBox code is tested, what has been tested so far, and what to run
for each change and each build. Built on 2026-11-01 from the Claude Code session
logs of 2026-10-04 to 2026-10-08, the Claude session of 2026-10-22 to 2026-10-30
and the fix log (`Hobby - ConnectBox\Claude\build-fixes-2026-10-22.md`, fixes 1–66).
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
- wifi-configurator suite: 14 of 29 fail (2026-11-01). Most tests are out of date (old function signatures, `range` instead of a list), but they also show a real bug: `scan.get_country_rules_block` matches the country code anywhere in a line (`AU` in `AUTO-BW`, `IR` in `NO-IR`, `JP` in `DFS-JP`), so with the test regulatory database AU, NO, IR, TD, DM and DO get no channels (hostapd then gets `channel=0`), SE and ET get 1–11, JP gets another country's list. Not fixed yet.
- hat-service repository suite: only a placeholder test (`assertTrue(True)`); the real front-panel tests are in `tests/harness/`.
- connectbox-manage `admin_login/` with a current admin-ui build (run on 2026-11-01 with the 26 Oct build).
- Raspberry Pi, CM4, Orange Pi Zero 2, Radxa CM3 builds on current OS releases (only
  the NanoPi NEO on Armbian 23.02 is tested).
- Central server (connectbox-chathost) build on a real Ubuntu 24.04 server, and
  phone-home against it (only the mock server so far).
- Native-speaker check of the shipped translations.
- Very old phones (iOS 9 / Android 4–5) against the current menus.

## Test record

Most recent first. One line per test run: date, what, result, where it is described.

| Date | Test | Result | Reference |
|---|---|---|---|
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
