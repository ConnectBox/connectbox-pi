"""Fix 51: PxUSBm fat_needs_check / run_fs_check.  usage: python3 test51_px.py <PxUSBm.py>"""
import importlib.util, os, struct, subprocess, sys, tempfile, time, types
from unittest import mock
sys.modules['pexpect'] = types.SimpleNamespace()
spec = importlib.util.spec_from_file_location("PxUSBm", sys.argv[1]); m = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:1]
spec.loader.exec_module(m)
m.logger = mock.MagicMock()
P = F = 0
def check(name, ok, detail=""):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))
d = tempfile.mkdtemp()
def img(name, size_mb, fatbits):
    p = os.path.join(d, name)
    with open(p, 'wb') as f: f.truncate(size_mb * 1024 * 1024)
    subprocess.run(['mkfs.fat', '-F', str(fatbits), p], capture_output=True, check=True)
    return p
def entry1(p):
    b = open(p, 'rb').read(512); bps, res = struct.unpack_from('<H', b, 11)[0], struct.unpack_from('<H', b, 14)[0]
    return res * bps
def setbits(p, fat32, clear_mask):
    off = entry1(p); f = open(p, 'r+b'); f.seek(off)
    if fat32:
        f.seek(off + 4); v = struct.unpack('<I', f.read(4))[0]; f.seek(off + 4); f.write(struct.pack('<I', v & ~clear_mask))
    else:
        f.seek(off + 2); v = struct.unpack('<H', f.read(2))[0]; f.seek(off + 2); f.write(struct.pack('<H', v & ~clear_mask))
    f.close()
# fat_needs_check opens '/dev/' + dev: point it at our images through a symlink-free path join
def need(path):
    with mock.patch.object(m, 'open', lambda p, *a, **k: open(path, *a, **k), create=True):
        return m.fat_needs_check('x')
f32 = img('f32.img', 300, 32); f16 = img('f16.img', 64, 16); f12 = img('f12.img', 2, 12)
check("FAT32 fresh from mkfs: clean, no check", need(f32) is False)
check("FAT16 fresh from mkfs: clean, no check", need(f16) is False)
check("FAT12: no flags, no check", need(f12) is False)
setbits(f32, True, 0x08000000); check("FAT32 not cleanly unmounted: check", need(f32) is True)
f32b = img('f32b.img', 300, 32); setbits(f32b, True, 0x04000000); check("FAT32 with I/O error flag: check", need(f32b) is True)
setbits(f16, False, 0x8000); check("FAT16 not cleanly unmounted: check", need(f16) is True)
def setstate(p, off):
    f = open(p, 'r+b'); f.seek(off); v = f.read(1)[0]; f.seek(off); f.write(bytes([v | 1])); f.close()
f32c = img('f32c.img', 300, 32); setstate(f32c, 0x41); check("FAT32 Linux dirty bit (boot sector 0x41): check", need(f32c) is True)
r = subprocess.run(['dosfsck', '-n', f32c], capture_output=True, text=True); check("dosfsck reads that same bit as dirty", 'Dirty bit' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
f16c = img('f16c.img', 64, 16); setstate(f16c, 0x25); check("FAT16 Linux dirty bit (boot sector 0x25): check", need(f16c) is True)
r = subprocess.run(['dosfsck', '-n', f16c], capture_output=True, text=True); check("dosfsck reads the FAT16 bit as dirty", 'Dirty bit' in r.stdout + r.stderr, (r.stdout + r.stderr)[-200:])
junk = os.path.join(d, 'junk'); open(junk, 'wb').write(os.urandom(4096)); check("no boot sector signature: check", need(junk) is True)
check("unreadable device: check", m.fat_needs_check('no-such-device-xyz') is True)
r = subprocess.run(['dosfsck', '-n', f32], capture_output=True, text=True)
check("dosfsck agrees the FAT32 image is marked dirty", 'not properly unmounted' in (r.stdout + r.stderr) or 'Dirty bit' in (r.stdout + r.stderr) or r.returncode != 0, r.stdout[-300:])
# run_fs_check
st = os.path.join(d, 'usbcheck.txt'); m.USB_CHECK_STATUS = st
check("quick check: exit code returned", m.run_fs_check(['sh', '-c', 'exit 1']) == 1)
check("quick check: panel message written", os.path.exists(st) and open(st).read() == m.USB_CHECK_TEXT)
os.remove(st)
m.FS_CHECK_SECS = 7
t = time.time(); mt = []
import threading
def watch():
    while time.time() - t < 6.5:
        try: mt.append(os.path.getmtime(st))
        except OSError: pass
        time.sleep(0.5)
w = threading.Thread(target=watch); w.start()
res = m.run_fs_check(['sleep', '30']); took = time.time() - t; w.join()
check("check past the limit: stopped, None returned (%.1f s)" % took, res is None and 6.5 < took < 10, (res, took))
check("panel message refreshed while it ran", len(set(mt)) >= 2, sorted(set(mt)))
check("stopped check leaves no process", subprocess.run(['pgrep', '-f', '^sleep 30$'], capture_output=True).returncode != 0)
check("command that cannot run: None", m.run_fs_check(['no-such-checker-xyz']) is None)
m.show_usb_check(False); check("show_usb_check(False) removes the message", not os.path.exists(st))
m.show_usb_check(False); check("... and again without error", True)
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
