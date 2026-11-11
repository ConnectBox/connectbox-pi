#!/bin/bash
# Runs the PxUSBm and mmiLoader harnesses (fixes 35-53) against this checkout.
# usage: bash tests/harness/run_all.sh [connectbox-hat-service checkout]   (default: ../connectbox-hat-service)
# Some tests also run the code from before the fixes (commit d1913b5, 24 Oct 2026) to show the
# test fails on it; set OLD_DIR to a folder holding that PxUSBm.py and mmiLoader.py to skip git.
# Linux only (reads /proc); test51_px needs mkfs.fat and dosfsck (package dosfstools).
HERE=$(dirname "$(realpath "$0")"); PI=$(realpath "$HERE/../.."); HAT=$(realpath "${1:-$PI/../connectbox-hat-service}")
F=$PI/ansible/roles/bootstrap/files; OLD=d1913b5
[ -f "$HAT/neo_batterylevelshutdown/hats.py" ] || { echo "connectbox-hat-service not found at $HAT (give its path)"; exit 2; }
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT; mkdir -p "$D/px35/orig" "$D/px35/new"
# Neutral file names: test38 and test_px_status look for running processes whose command line
# contains "mmiLoader.py", so no command line here may contain that name.
cp "$F/usr_local_connectbox_bin_mmiLoader.py" "$D/loader_new.py"
cp "$F/usr_local_connectbox_bin_PxUSBm.py" "$D/px.py"; cp "$D/px.py" "$D/px35/new/PxUSBm.py"
cp "$HAT/neo_batterylevelshutdown/hats.py" "$D/hats.py"
if [ -n "$OLD_DIR" ]; then cp "$OLD_DIR/mmiLoader.py" "$D/loader_old.py"; cp "$OLD_DIR/PxUSBm.py" "$D/px35/orig/PxUSBm.py"
else git -C "$PI" show $OLD:ansible/roles/bootstrap/files/usr_local_connectbox_bin_mmiLoader.py > "$D/loader_old.py" &&
     git -C "$PI" show $OLD:ansible/roles/bootstrap/files/usr_local_connectbox_bin_PxUSBm.py > "$D/px35/orig/PxUSBm.py" ||
     { echo "could not get the $OLD files from git (set OLD_DIR)"; exit 2; }; fi
FAILED=0
run() { local name=$1; shift; echo "== $name"; if (cd "$D" && python3 "$@") > "$D/out.txt" 2>&1; then grep -v "^[[:space:]]*$" "$D/out.txt" | tail -n 1; else cat "$D/out.txt"; FAILED=1; fi
        grep -q "FAIL\]\|\[FAIL\|^FAIL" "$D/out.txt" && FAILED=1; }
run "px35 (key moved off usb0; old and new)"       "$HERE/px35.py" "$D/px35"
run "test38 (stale status file; old and new)"      "$HERE/test38.py" loader_new.py loader_old.py hats.py
run "testwc (status file writes)"                  "$HERE/testwc.py" loader_new.py
run "test47 (default language)"                    "$HERE/test47.py" loader_new.py
run "test_make_zip (mmiLoader.make_zip)"           "$HERE/test_make_zip.py" loader_new.py
# test38 leaves short-lived fake loaders running; test_px_status needs none left
for i in $(seq 60); do pgrep -f "mmiLoader[.]py" > /dev/null || break; sleep 1; done
run "test_px_status (start-up status file)"        "$HERE/test_px_status.py" px.py
run "test51_px (FAT check before mounting)"        "$HERE/test51_px.py" px.py
run "test53 (dead / stacked mounts)"               "$HERE/test53.py" px.py
ADMIN_UI=$(realpath "$PI/../connectbox-admin-ui" 2>/dev/null); [ -f "$ADMIN_UI/src/js/admin/hdmi_admin.js" ] || ADMIN_UI=""
run "hdmi_test (HDMI player, splash, page patches)" "$HERE/hdmi_test.py" "$PI" $ADMIN_UI
[ $FAILED = 0 ] && echo "ALL PASSED" || echo "SOME TESTS FAILED"; exit $FAILED
