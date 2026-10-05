#!/usr/bin/env python3
"""
Simulation tests for PxUSBm.mountCheck() — the USB mount / unmount / index loop.

Each scenario feeds mountCheck() a fake `lsblk` listing (what the kernel shows
on that 3 s poll) and records every shell command it runs instead of running
it.  This checks which devices get mounted, with which options, when mmiLoader
is started, and how removal is cleaned up, without a device or root.

Run:  python3 test_PxUSBm_mount.py
"""

import os
import sys
import types
import importlib.util
import unittest.mock as mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# pexpect is only used for partition expansion; stub it so the module imports anywhere
sys.modules.setdefault('pexpect', types.ModuleType('pexpect'))

_spec = importlib.util.spec_from_file_location(
	"PxUSBm", os.path.join(SCRIPT_DIR, "usr_local_connectbox_bin_PxUSBm.py"))
PxUSBm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PxUSBm)

PASS = 0
FAIL = 0
ERRORS = []


def check(label, condition, detail=""):
	global PASS, FAIL
	if condition:
		print(f"  [PASS] {label}")
		PASS += 1
	else:
		print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
		FAIL += 1
		ERRORS.append(label + (": " + detail if detail else ""))


HEADER = "NAME        MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT\n"
ROOT   = "mmcblk0     179:0    0 29.7G  0 disk \n└─mmcblk0p1 179:1    0 29.7G  0 part /\n"


def disk(name, mountpoint=""):
	return f"{name:<12}8:0    1 28.6G  0 disk {mountpoint}\n"


def part(name, mountpoint=""):
	return f"└─{name:<10}8:1    1 28.6G  0 part {mountpoint}\n"


class FakeDevice:
	"""
	Stands in for the kernel and shell while mountCheck() runs.

	listing   — current lsblk text (HEADER + ROOT are added automatically)
	fstypes   — device name -> file system type reported by `lsblk -dno FSTYPE`
	mount_rc  — return code for `mount` commands (0 = success)
	commands  — every os.system command, in order
	"""
	def __init__(self):
		self.listing = ""
		self.fstypes = {}
		self.mount_rc = 0
		self.commands = []
		self.files = set()          # sentinel files that "exist"

	def lsblk_text(self):
		return HEADER + self.listing + ROOT

	def system(self, cmd):
		self.commands.append(cmd)
		if cmd.startswith("mount "):
			return self.mount_rc
		if cmd.startswith("/bin/sh -c '/usr/bin/test"):
			return 256                       # no enable-ssh / upgrade.py on the USB
		return 0

	def popen(self, cmd):
		class P:
			def __init__(self, text): self.text = text
			def read(self): return self.text
			def close(self): pass
		return P(self.lsblk_text() if cmd == 'lsblk' else "")

	def run(self, args, **kwargs):
		if args[0] == 'systemctl':
			return types.SimpleNamespace(stdout="not-found\n", returncode=0)
		dev = args[-1].replace('/dev/', '')
		return types.SimpleNamespace(stdout=self.fstypes.get(dev, "") + "\n", returncode=0)

	def isfile(self, path):
		return path in self.files

	def remove(self, path):
		self.files.discard(path)

	def open(self, path, mode='r', *a, **k):
		if path == '/tmp/.usb0_indexed':
			self.files.add(path)
			return mock.MagicMock()
		return open(path, mode, *a, **k)

	def poll(self):
		"""Run one mountCheck() pass; return the commands it issued."""
		start = len(self.commands)
		PxUSBm.mountCheck()
		return self.commands[start:]


def fresh_state():
	"""Reset PxUSBm's module-level mount tables between scenarios."""
	PxUSBm.mnt = [-1] * 11
	PxUSBm.loc = [-1] * 11
	PxUSBm.total = 0
	PxUSBm.whole_disk.clear()
	PxUSBm.failed_mounts.clear()


def run_with(dev, fn):
	fresh_state()
	PxUSBm.DEBUG = 0
	PxUSBm.Brand = {"usb0NoMount": 0, "Brand": "ConnectBox"}
	PxUSBm.logger = mock.MagicMock()
	uname = mock.MagicMock()
	uname.communicate.return_value = (b"5.15.93-sunxi\n", b"")
	with mock.patch.object(PxUSBm.os, "system", dev.system), \
		mock.patch.object(PxUSBm.os, "popen", dev.popen), \
		mock.patch.object(PxUSBm.os, "remove", dev.remove), \
		mock.patch.object(PxUSBm.os.path, "isfile", dev.isfile), \
		mock.patch.object(PxUSBm.os.path, "exists", lambda p: True), \
		mock.patch.object(PxUSBm.subprocess, "run", dev.run), \
		mock.patch.object(PxUSBm, "Popen", lambda *a, **k: uname), \
		mock.patch.object(PxUSBm, "open", dev.open, create=True):
		fn()


def started_loader(cmds):
	return any("systemd-run --unit=connectbox-loader" in c for c in cmds)


def mounts(cmds):
	return [c for c in cmds if c.startswith("mount ")]


# ── Scenarios ────────────────────────────────────────────────────────────────

def scenario_fat_partition():
	print("\n-- Scenario 1: FAT32 stick with a partition (the usual case) --")
	dev = FakeDevice()
	dev.fstypes = {"sda1": "vfat"}

	def body():
		dev.listing = disk("sda") + part("sda1")
		cmds = dev.poll()
		check("S1: dosfsck runs on FAT", any(c.startswith("dosfsck -a /dev/sda1") for c in cmds))
		check("S1: mounted sda1 with utf8 at usb0",
			mounts(cmds) == ["mount /dev/sda1 -t auto -o noatime,nodev,nosuid,utf8 /media/usb0"], str(mounts(cmds)))
		check("S1: partitioned disk line not probed as whole disk", "sda" not in PxUSBm.whole_disk)

		dev.listing = disk("sda") + part("sda1", "/media/usb0")
		cmds = dev.poll()
		check("S1: mmiLoader started on next poll", started_loader(cmds), str(cmds))
		stop_i = [i for i, c in enumerate(cmds) if c.startswith("systemctl stop connectbox-loader")]
		run_i = [i for i, c in enumerate(cmds) if "systemd-run --unit=connectbox-loader" in c]
		check("S1: loader stops any previous run first", stop_i and run_i and stop_i[0] < run_i[0], str(cmds))
		check("S1: stop does not use --wait (rejected by systemd 247)", not any("stop --wait" in c for c in cmds))

		cmds = dev.poll()
		check("S1: mmiLoader not restarted on later polls", not started_loader(cmds) and not mounts(cmds), str(cmds))

		dev.listing = ""
		cmds = dev.poll()
		check("S1: removal stops the loader", any(c.startswith("systemctl stop connectbox-loader") for c in cmds))
		check("S1: removal lazily unmounts by mount point", "umount -l /media/usb0" in cmds, str(cmds))
		check("S1: removal clears the indexed sentinel", '/tmp/.usb0_indexed' not in dev.files)
		check("S1: mount table empty after removal", PxUSBm.mnt[0] == -1 and PxUSBm.loc[0] == -1)

		dev.listing = disk("sda") + part("sda1")
		cmds = dev.poll()
		dev.listing = disk("sda") + part("sda1", "/media/usb0")
		cmds += dev.poll()
		check("S1: re-insert mounts and indexes again", mounts(cmds) and started_loader(cmds))
	run_with(dev, body)


def scenario_ext4_whole_disk():
	print("\n-- Scenario 2: ext4 formatted with no partition (mkfs.ext4 /dev/sdb) --")
	dev = FakeDevice()
	dev.fstypes = {"sdb": "ext4"}

	def body():
		dev.listing = disk("sdb")
		cmds = dev.poll()
		check("S2: no dosfsck/ntfsfix on ext4", not any(c.startswith(("dosfsck", "ntfsfix")) for c in cmds), str(cmds))
		check("S2: mounted whole disk as ext4 without utf8",
			mounts(cmds) == ["mount /dev/sdb -t ext4 -o noatime,nodev,nosuid /media/usb0"], str(mounts(cmds)))
		check("S2: drive recorded as whole-disk", PxUSBm.whole_disk == {"b"} and PxUSBm.mnt[0] == ord("b"))

		dev.listing = disk("sdb", "/media/usb0")
		cmds = dev.poll()
		check("S2: whole disk still seen as present", "umount -l /media/usb0" not in cmds, str(cmds))
		check("S2: mmiLoader started", started_loader(cmds))

		dev.listing = ""
		cmds = dev.poll()
		check("S2: removal unmounts usb0", "umount -l /media/usb0" in cmds, str(cmds))
		check("S2: whole-disk flag cleared", not PxUSBm.whole_disk)
	run_with(dev, body)


def scenario_ext4_partition():
	print("\n-- Scenario 3: ext4 on a partition --")
	dev = FakeDevice()
	dev.fstypes = {"sdc1": "ext4"}

	def body():
		dev.listing = disk("sdc") + part("sdc1")
		cmds = dev.poll()
		check("S3: mounted sdc1 as ext4 without utf8",
			mounts(cmds) == ["mount /dev/sdc1 -t ext4 -o noatime,nodev,nosuid /media/usb0"], str(mounts(cmds)))
		check("S3: not flagged as whole disk", not PxUSBm.whole_disk)
	run_with(dev, body)


def scenario_blank_and_failed():
	print("\n-- Scenario 4: blank stick, and a stick that will not mount --")
	dev = FakeDevice()

	def body():
		dev.listing = disk("sdd")                       # no partitions, no file system
		cmds = dev.poll()
		check("S4: blank disk ignored", not mounts(cmds), str(cmds))

		dev.fstypes = {"sde1": "vfat"}
		dev.mount_rc = 8192                              # every mount attempt fails
		dev.listing = disk("sde") + part("sde1")
		cmds = dev.poll()
		check("S4: failed mount attempted", len(mounts(cmds)) >= 1)
		check("S4: failed mount not recorded as mounted", PxUSBm.mnt[0] == -1, str(PxUSBm.mnt))
		check("S4: failed mount does not start mmiLoader", not started_loader(cmds))
		cmds = dev.poll()
		check("S4: failed stick not retried every poll", not mounts(cmds) and not any(c.startswith("dosfsck") for c in cmds), str(cmds))

		dev.listing = ""
		dev.poll()
		dev.mount_rc = 0
		dev.listing = disk("sde") + part("sde1")
		cmds = dev.poll()
		check("S4: retried after re-insert", len(mounts(cmds)) == 1, str(mounts(cmds)))
	run_with(dev, body)


def scenario_already_mounted_whole_disk():
	print("\n-- Scenario 5: whole-disk USB already mounted when PxUSBm starts --")
	dev = FakeDevice()
	dev.fstypes = {"sdb": "ext4"}

	def body():
		dev.listing = disk("sdb", "/media/usb0")
		cmds = dev.poll()
		check("S5: registered without remounting", not mounts(cmds) and PxUSBm.mnt[0] == ord("b"), str(cmds))
		check("S5: registered as whole disk", "b" in PxUSBm.whole_disk)
		cmds = dev.poll()
		check("S5: indexed on next poll", started_loader(cmds))
	run_with(dev, body)


if __name__ == '__main__':
	scenario_fat_partition()
	scenario_ext4_whole_disk()
	scenario_ext4_partition()
	scenario_blank_and_failed()
	scenario_already_mounted_whole_disk()

	print(f"\n{'='*60}")
	print(f"Results: {PASS} passed, {FAIL} failed")
	if ERRORS:
		print("Failed checks:")
		for e in ERRORS:
			print(f"  - {e}")
	print('='*60)
	sys.exit(0 if FAIL == 0 else 1)
