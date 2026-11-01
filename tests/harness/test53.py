"""Fix 53: dead/stacked USB mounts after a PxUSBm restart.  usage: python3 test53.py <PxUSBm.py>"""
import importlib.util, io, os, sys, types
from unittest import mock
sys.modules['pexpect'] = types.SimpleNamespace()
spec = importlib.util.spec_from_file_location("PxUSBm", sys.argv[1]); m = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:1]; spec.loader.exec_module(m); m.logger = mock.MagicMock()
P = F = 0
def check(name, ok, detail=""):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))
class Box:
    """Fake /proc/mounts (a list, in mount order), device nodes, os.system."""
    def __init__(self, mounts, devices, marker=False):
        self.mounts = list(mounts); self.devices = set(devices); self.cmds = []; self.removed = []
        self.marker = marker
    def open(self, path, *a, **k):
        if path == '/proc/mounts':
            return io.StringIO("".join("%s %s vfat rw 0 0\n" % mt for mt in self.mounts))
        raise OSError(path)
    def system(self, cmd):
        self.cmds.append(cmd)
        if cmd.startswith("umount -l "):
            target = cmd.split()[2]
            for i in range(len(self.mounts) - 1, -1, -1):        # lazy umount removes the top mount
                if self.mounts[i][1] == target:
                    del self.mounts[i]; return 0
            return 8192
        return 0
    def exists(self, p): return p in self.devices
    def remove(self, p):
        if p == '/tmp/.usb0_indexed' and self.marker: self.marker = False; self.removed.append(p); return
        raise OSError(p)
    def patches(self):
        return [mock.patch.object(m, "open", self.open, create=True), mock.patch.object(m.os, "system", self.system),
                mock.patch.object(m.os.path, "exists", self.exists), mock.patch.object(m.os, "remove", self.remove),
                mock.patch.object(m.os.path, "realpath", lambda p: p)]
def run(box, fn, *args):
    ps = box.patches(); [p.start() for p in ps]
    try: return fn(*args)
    finally: [p.stop() for p in ps]
# the .153 state: dead sda1 underneath, sdb1 on top
b = Box([("/dev/sda1", "/media/usb0"), ("/dev/sdb1", "/media/usb0")], {"/dev/sdb1"})
check("stacked mounts: mounted_device gives the one on top (sdb1)", run(b, m.mounted_device, "/media/usb0") == "/dev/sdb1")
b = Box([("/dev/sdb1", "/media/usb0")], {"/dev/sdb1"}); check("single mount: that device", run(b, m.mounted_device, "/media/usb0") == "/dev/sdb1")
b = Box([], set()); check("nothing mounted: ''", run(b, m.mounted_device, "/media/usb0") == "")
# clear_dead_mounts before a mount
b = Box([("/dev/sda1", "/media/usb0")], set()); run(b, m.clear_dead_mounts, "/media/usb0")
check("dead mount at the slot: lazily unmounted", b.mounts == [] and b.cmds == ["umount -l /media/usb0 2>/dev/null"], b.cmds)
b = Box([("/dev/sda1", "/media/usb0")], {"/dev/sda1"}); run(b, m.clear_dead_mounts, "/media/usb0")
check("live mount at the slot: left alone", b.mounts == [("/dev/sda1", "/media/usb0")] and b.cmds == [], b.cmds)
b = Box([("/dev/sda1", "/media/usb0"), ("/dev/sdc1", "/media/usb0")], set()); run(b, m.clear_dead_mounts, "/media/usb0")
check("two dead mounts stacked: both removed", b.mounts == [], b.mounts)
b = Box([], set()); run(b, m.clear_dead_mounts, "/media/usb0"); check("empty slot: nothing run", b.cmds == [])
# release_usb_slots at start-up
b = Box([("/dev/sda1", "/media/usb0"), ("/dev/sdb1", "/media/usb0"), ("/dev/sdc1", "/media/usb1"), ("/dev/sdd1", "/media/usb11"),
         ("/dev/mmcblk0p1", "/")], {"/dev/sdb1", "/dev/sdc1", "/dev/sdd1"}, marker=True)
run(b, m.release_usb_slots)
check("start-up: every /media/usb0-9 mount released", b.mounts == [("/dev/sdd1", "/media/usb11"), ("/dev/mmcblk0p1", "/")], b.mounts)
check("start-up: /media/usb11 (front panel copy) and / left alone", ("/dev/sdd1", "/media/usb11") in b.mounts)
check("start-up: usb0 indexed marker removed", b.removed == ['/tmp/.usb0_indexed'], b.removed)
b = Box([("/dev/sda1", "/media/usb0")], set()); b.system = lambda c: (b.cmds.append(c), 1)[1]
run(b, m.release_usb_slots); check("start-up: umount failing does not loop for ever", len(b.cmds) == 1, b.cmds)
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
