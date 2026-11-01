"""Fix 48a: PxUSBm start-up removes /tmp/creating_menus.txt only when no mmiLoader runs.
usage: python3 test_px_status.py <PxUSBm.py>"""
import os, re, subprocess, sys, tempfile, time
src = open(sys.argv[1]).read()
m = re.search(r'    if os\.path\.exists\("/tmp/creating_menus\.txt"\).*?\n(?:        .*\n)+', src)
assert m, "block not found"
d = tempfile.mkdtemp(); st = os.path.join(d, "creating_menus.txt")
code = "\n".join(l[4:] for l in m.group(0).replace("/tmp/creating_menus.txt", st).splitlines())
P = F = 0
def check(name, ok):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name)
def run(): exec(code, {"os": os, "subprocess": subprocess})
open(st, "w").write("Indexing USB"); run(); check("no loader running: stale file removed", not os.path.exists(st))
run(); check("no file: no error", True)
fake = os.path.join(d, "mmiLoader.py"); open(fake, "w").write("import time; time.sleep(20)\n")
p = subprocess.Popen([sys.executable, fake]); time.sleep(0.5)
open(st, "w").write("Indexing 40%"); run(); check("loader running: file kept", os.path.exists(st))
p.kill(); p.wait(); run(); check("after the loader ends: removed", not os.path.exists(st))
print(f"Results: {P} passed, {F} failed"); sys.exit(1 if F else 0)
