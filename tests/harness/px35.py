import sys, types, os, importlib.util, tempfile, io
from unittest import mock
W = sys.argv[1]
PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print("  [PASS] " + label)
    else: FAIL += 1; print("  [FAIL] " + label + ((": " + str(detail)) if detail else ""))
sys.modules["pexpect"] = types.ModuleType("pexpect")
def load(path):
    spec = importlib.util.spec_from_file_location("px", path); m = importlib.util.module_from_spec(spec)
    with mock.patch("logging.handlers.RotatingFileHandler", side_effect=lambda *a, **k: __import__("logging").NullHandler()), \
         mock.patch("logging.handlers.SysLogHandler", side_effect=lambda *a, **k: __import__("logging").NullHandler()):
        spec.loader.exec_module(m)
    return m

LSBLK_UNMOUNTED = "NAME        MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\nsda           8:0    1 28.6G  0 disk \n`-sda1        8:1    1 28.6G  0 part \nmmcblk0     179:0    0 59.6G  0 disk \n`-mmcblk0p1 179:1    0   59G  0 part /\n"
LSBLK_AT_USB11 = LSBLK_UNMOUNTED.replace("0 part \nmmc", "0 part /media/usb11\nmmc")

def run(path, lsblk, mounts, label):
    m = load(path)
    tmp = tempfile.mkdtemp(); sentinel = os.path.join(tmp, ".usb0_indexed"); open(sentinel, "w").close()
    m.Brand = {"usb0NoMount": "0"}; m.DEBUG = 0; m.logger = __import__("logging").getLogger("px")
    m.mnt[:] = [-1] * 11; m.loc[:] = [-1] * 11
    m.mnt[0] = ord('a'); m.loc[0] = ord('0')            # PxUSBm mounted sda1 at /media/usb0 earlier
    systems = []
    def fake_system(cmd):
        systems.append(cmd)
        return 0
    class P:
        def __init__(s, out): s.out = out
        def read(s): return s.out
        def close(s): pass
    real_open = open
    def fake_open(p, *a, **k):
        if p == "/proc/mounts": return io.StringIO(mounts)
        if p == "/tmp/.usb0_indexed": return real_open(sentinel, *a, **k)
        return real_open(p, *a, **k)
    removed = []
    real_remove = os.remove
    real_exists = os.path.exists; real_isfile = os.path.isfile
    def fake_remove(p):
        if p == "/tmp/.usb0_indexed": removed.append(p); return real_remove(sentinel) if real_exists(sentinel) else None
        if p.startswith("/tmp/.internal"): removed.append(p); return None
        return real_remove(p)
    with mock.patch.object(m.os, "popen", side_effect=lambda c: P(lsblk if "lsblk" in c else "")), \
         mock.patch.object(m.os, "system", side_effect=fake_system), \
         mock.patch.object(m.os.path, "isfile", side_effect=lambda p: real_exists(sentinel) if p == "/tmp/.usb0_indexed" else real_isfile(p)), \
         mock.patch.object(m.os.path, "exists", side_effect=lambda p: True if p.startswith("/media/usb") else real_exists(p)), \
         mock.patch.object(m.os, "remove", side_effect=fake_remove), \
         mock.patch("builtins.open", side_effect=fake_open), \
         mock.patch.object(m, "get_fstype", return_value="vfat"), \
         mock.patch.object(m, "start_content_loader", side_effect=lambda: systems.append("LOADER")), \
         mock.patch.object(m, "Popen") as pop:
        pop.return_value.communicate.return_value = (b"6.1.11-sunxi", b"")
        m.mountCheck()
    return m, systems, removed

print("== PxUSBm: key moved off usb0 by the front panel ==")
for path, name in ((W + "/orig/PxUSBm.py", "old"), (W + "/new/PxUSBm.py", "new")):
    m, sy, rm = run(path, LSBLK_UNMOUNTED, "/dev/mmcblk0p1 / ext4 rw 0 0\n", name)
    mounts = [c for c in sy if c.startswith("mount ")]
    print("   %s: slots %s / %s, mount commands %s" % (name, [chr(x) if x > 0 else '-' for x in m.mnt[:3]],
          [chr(x) if x > 0 else '-' for x in m.loc[:3]], mounts))
    if name == "old":
        check("old code: usb0 slot kept, key mounted again at /media/usb1 (what the test box showed)",
              any(c.endswith("/media/usb1") for c in mounts) and m.loc[0] == ord('0'), (mounts, m.loc[:3]))
    else:
        check("new code: stale usb0 slot forgotten, key mounted again at /media/usb0",
              any(c.endswith("/media/usb0") for c in mounts) and not any(c.endswith("/media/usb1") for c in mounts), mounts)
        check("new code: usb0 'indexed' marker cleared so the key is indexed again", "/tmp/.usb0_indexed" in rm, rm)

m, sy, rm = run(W + "/new/PxUSBm.py", LSBLK_AT_USB11, "/dev/sda1 /media/usb11 vfat rw 0 0\n", "new")
check("key mounted at /media/usb11 by the front panel (mount checks resumed early): slot forgotten, no second mount",
      not any(c.startswith("mount ") for c in sy) and m.loc[0] == -1, (sy, m.loc[:3]))
m, sy, rm = run(W + "/new/PxUSBm.py", LSBLK_UNMOUNTED.replace("0 part \nmmc", "0 part /media/usb0\nmmc"), "/dev/sda1 /media/usb0 vfat rw 0 0\n", "new")
check("normal case (key still at /media/usb0): slot kept, nothing mounted, nothing cleared",
      m.loc[0] == ord('0') and not any(c.startswith("mount ") for c in sy) and rm == [], (sy, rm))
print("Results: %d passed, %d failed" % (PASS, FAIL))
