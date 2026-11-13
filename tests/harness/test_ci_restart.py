"""PxUSBm client Wi-Fi restart (2026-11-13).  usage: python3 test_ci_restart.py <PxUSBm.py>

check_stat_CI() restarted the client with "ifdown; rm control socket; ifup".
When ifdown did not stop the running wpa_supplicant, its socket was deleted
while it ran and ifup started a second one on the same interface (seen on the
CM5: two on wlan0, "Failed to initiate sched scan" every 8 s, no connection).
Checked here, with a fake /proc, a fake socket folder and no real commands:
- wpa_supplicant_pids() finds every wpa_supplicant for the interface ("-i dev"
  and "-idev"), and not the global instance, other interfaces or a shell whose
  command line mentions wpa_supplicant;
- restart_client() runs ifdown, stops those processes (SIGTERM, then SIGKILL
  for one that stays), removes the sockets only after that, then runs ifup;
- check_stat_CI() hands the restart to a background thread running
  restart_client, and does nothing while the client is up and answers.
Fails on the code before the fix (no wpa_supplicant_pids / restart_client).
"""
import importlib.util, os, signal, sys, tempfile, types
from unittest import mock
sys.modules['pexpect'] = types.SimpleNamespace()
spec = importlib.util.spec_from_file_location("PxUSBm", sys.argv[1]); m = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:1]
spec.loader.exec_module(m)
m.logger = mock.MagicMock()
P = F = 0


def check(name, ok, detail=""):
    """Count and print one check."""
    global P, F
    P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))


have = all(hasattr(m, n) for n in ("wpa_supplicant_pids", "stop_wpa_supplicants", "restart_client"))
check("PxUSBm has wpa_supplicant_pids, stop_wpa_supplicants and restart_client", have)
if not have:
    print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1)

# -- a fake /proc ---------------------------------------------------------------------
T = tempfile.mkdtemp()
proc = os.path.join(T, "proc"); os.makedirs(proc)
def fake(pid, argv):
    """Write a /proc/<pid>/cmdline the way the kernel does (NUL-separated)."""
    os.makedirs(os.path.join(proc, str(pid)), exist_ok=True)
    open(os.path.join(proc, str(pid), "cmdline"), "wb").write(("\0".join(argv) + "\0").encode())
fake(2485, ["/usr/sbin/wpa_supplicant", "-u", "-s", "-O", "DIR=/run/wpa_supplicant", "GROUP=netdev"])
fake(4366, ["/usr/sbin/wpa_supplicant", "-s", "-B", "-P", "/run/wpa_supplicant.wlan0.pid", "-i", "wlan0", "-D", "nl80211,wext", "-c", "/etc/wpa_supplicant/wpa_supplicant.conf"])
fake(5110, ["/usr/sbin/wpa_supplicant", "-s", "-B", "-iwlan0", "-c", "/etc/wpa_supplicant/wpa_supplicant.conf"])
fake(6000, ["/usr/sbin/wpa_supplicant", "-B", "-i", "wlan1", "-c", "/etc/x.conf"])
fake(7000, ["sh", "-c", "pkill -f 'wpa_supplicant .*-i wlan0'"])
fake(7001, ["/usr/sbin/wpa_supplicant", "-B", "-i", "wlan01"])
os.makedirs(os.path.join(proc, "self"), exist_ok=True)
m.PROC_DIR = proc
check("finds both wlan0 supplicants (-i wlan0 and -iwlan0), nothing else", sorted(m.wpa_supplicant_pids("wlan0")) == [4366, 5110], m.wpa_supplicant_pids("wlan0"))
check("wlan1 finds only its own", m.wpa_supplicant_pids("wlan1") == [6000], m.wpa_supplicant_pids("wlan1"))
check("no /proc folder: empty list", (setattr(m, "PROC_DIR", os.path.join(T, "none")) or m.wpa_supplicant_pids("wlan0")) == [])
m.PROC_DIR = proc

# -- restart_client: order of steps --------------------------------------------------------
ctrl = os.path.join(T, "ctrl"); os.makedirs(ctrl); m.WPA_CTRL_DIR = ctrl
for n in ("wlan0", "p2p-dev-wlan0", "wlan1"):
    open(os.path.join(ctrl, n), "w").close()
events = []
def fake_run(cmd, **k):
    """Record ifdown/ifup and the socket state at that moment."""
    events.append((cmd[0], sorted(os.listdir(ctrl))))
    return types.SimpleNamespace(returncode=0)
def fake_kill(pid, sig):
    """SIGTERM ends 4366; 5110 ignores SIGTERM and ends only on SIGKILL."""
    events.append(("kill", pid, sig, sorted(os.listdir(ctrl))))
    if sig == signal.SIGKILL or pid != 5110:
        import shutil; shutil.rmtree(os.path.join(proc, str(pid)), ignore_errors=True)
with mock.patch.object(m.subprocess, "run", fake_run), mock.patch.object(m.os, "kill", fake_kill), \
     mock.patch.object(m, "stop_wpa_supplicants", lambda dev, wait_secs=5.0, f=m.stop_wpa_supplicants: f(dev, 0.5)):
    m.restart_client("wlan0")
names = [e[0] for e in events]
check("steps: ifdown, then the kills, then ifup", names[0] == "ifdown" and names[-1] == "ifup" and "kill" in names[1:-1], names)
kills = [(e[1], e[2]) for e in events if e[0] == "kill"]
check("SIGTERM to both wlan0 supplicants", (4366, signal.SIGTERM) in kills and (5110, signal.SIGTERM) in kills, kills)
check("SIGKILL only to the one that stayed", [k for k in kills if k[1] == signal.SIGKILL] == [(5110, signal.SIGKILL)], kills)
check("global, wlan1 and the shell are not signalled", not any(k[0] in (2485, 6000, 7000, 7001) for k in kills), kills)
check("sockets still there while the processes are being stopped", all("wlan0" in e[3] for e in events if e[0] == "kill"))
check("wlan0 and p2p-dev-wlan0 sockets gone before ifup; wlan1's kept", events[-1][1] == ["wlan1"], events[-1])
check("restart was logged with the stopped pids", any("stopped wpa_supplicant 4366" in str(c) or "stopped wpa_supplicant 5110" in str(c) for c in m.logger.info.call_args_list), m.logger.info.call_args_list)

# -- check_stat_CI ---------------------------------------------------------------------------
real_open = open
def opener(flags):
    """open() that serves /sys/class/net/<dev>/flags from a string."""
    def o(path, *a, **k):
        if str(path).startswith("/sys/class/net/"):
            import io; return io.StringIO(flags)
        return real_open(path, *a, **k)
    return o
started = []
class FakeThread:
    """Records the thread target instead of running it."""
    def __init__(self, target=None, args=(), daemon=None): self.t = (target, args)
    def start(self): started.append(self.t)
def run_check(flags, answers):
    """check_stat_CI(0) with the given flags and wpa_cli result."""
    with mock.patch.object(m, "open", opener(flags), create=True), \
         mock.patch.object(m.subprocess, "run", lambda cmd, **k: types.SimpleNamespace(returncode=0 if answers else 1)), \
         mock.patch.object(m.threading, "Thread", FakeThread), mock.patch.object(m, "check_CI", lambda: 1):
        return m.check_stat_CI(0)
m.ci_restart[0] = 0.0
check("up and answering: no restart", run_check("0x1003", True) == 0 and started == [], started)
check("does not answer: restart in a thread running restart_client('wlan0')",
      run_check("0x1003", False) == 0 and started == [(m.restart_client, ("wlan0",))], started)
check("again within 5 minutes: no second restart", run_check("0x1002", False) == 1 and len(started) == 1, started)
print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
