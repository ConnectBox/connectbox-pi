# PxUSBm, mmiLoader and on-box test harnesses

Tests written for the October–November 2026 fixes (35–64). Each harness takes the file under test as
its argument, so it can also be run on old code to show the test fails there.

## Run the PxUSBm / mmiLoader harnesses

```
bash tests/harness/run_all.sh [path to connectbox-hat-service]   # default: ../connectbox-hat-service
```

Linux, Python 3, git; `test51_px.py` needs `mkfs.fat` and `dosfsck` (package dosfstools).
`px35.py` and `test38.py` also run the code from before the fixes (commit d1913b5, 24 Oct 2026), which
`run_all.sh` takes from git; set `OLD_DIR` to a folder holding that `PxUSBm.py` and `mmiLoader.py` instead.

Running them by hand: `test38.py` and `test_px_status.py` look for running processes whose command line
contains `mmiLoader.py`. Copy the files under test to neutral names first (`loader_new.py`,
`loader_old.py`, `px.py`, as `run_all.sh` does) and run `test_px_status.py` only once test38's fake
loaders (30 s) have ended.

| File | Covers | Argument(s) |
|---|---|---|
| `px35.py` | PxUSBm mountCheck slot booking (key moved off usb0) | folder with `orig/PxUSBm.py` (old) and `new/PxUSBm.py` |
| `test38.py` | stale front-panel status file; mmiLoader SIGTERM / early exit | new mmiLoader, old mmiLoader, hat-service `hats.py` |
| `testwc.py` | `.webcompress` opt-in download zips | mmiLoader |
| `test47.py` | default language (eng/en/en-GB, no English → first) | mmiLoader |
| `test_make_zip.py` | `mmiLoader.make_zip` (same as make_archive, SIGTERM stops, no .part left) | mmiLoader |
| `test_px_status.py` | PxUSBm start-up removes /tmp/creating_menus.txt only when no loader runs | PxUSBm |
| `test51_px.py` | `fat_needs_check` on mkfs.fat images, `run_fs_check` 120 s limit, "Checking USB" message | PxUSBm |
| `test53.py` | dead / stacked mounts after a PxUSBm restart | PxUSBm |
| `hdmi_test.py` | HDMI screen (2026-11-11): which files the player may play, playlist reading, HDMI port and sound card, play / back-to-playlist / splash with a fake mpv, splash picture, `patch_admin_hdmi.py` and `patch_hdmi_button.py` (once, idempotent, built-in release, unknown page; embedded script = admin-ui copy) | hdmi-screen role |

Results on 2026-11-01 (connectbox-pi fc7d58c, hat-service 731a6ff): 5, 19, 7, 9, 8, 4, 21 and 11 passed, none failed.
The repository suites `ansible/roles/bootstrap/files/test_PxUSBm_mount.py` (32) and `test_mmiLoader.py`
(317; needs mammoth, openpyxl, xlrd, xlwt, olefile, python-pptx) also passed.

## On a box

`phonehome64/` (fix 64): phonehome.py end to end as www-data against a fake cloud server, with a
bind-mounted test copy of brand.j2. Copy the folder to the box's `/tmp/phonehome64` (from git, not the
Windows working tree), put the phonehome.py to test there as `new_phonehome.py`, then as root
`bash /tmp/phonehome64/run_test.sh`. Afterwards remove the `{"sync":true}` line it adds to the usage log.

`node22/` (fix 60): moving an existing box from Node 16 to Node 22 by hand. New builds already install
Node 22. `node22_fetch.sh` downloads and checks Node 22 into /opt; `node22_test.sh` runs Node 22 beside
Node 16 and compares 24 read-only `get.*` answers and a second server on port 5012; `node22_switch.sh`
backs up and switches pm2 to Node 22; `node22_after.sh` checks pm2 and the answers afterwards.
Run as root on the box, in that order.

See `docs/testing.md` for all tests and when to run them.
