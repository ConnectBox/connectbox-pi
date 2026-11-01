"""Fix 48b: mmiLoader.make_zip.  usage: python3 test_make_zip.py <mmiLoader.py>"""
import importlib.util, os, shutil, signal, subprocess, sys, tempfile, textwrap, time, types, zipfile
MMI = sys.argv[1]
sys.modules["indexer"] = types.SimpleNamespace(process_dir=lambda *a: None)
spec = importlib.util.spec_from_file_location("mmiLoader", MMI); m = importlib.util.module_from_spec(spec)
sys.modules["mmiLoader"] = m; spec.loader.exec_module(m)
P = F = 0
def check(name, ok, detail=""):
    global P, F; P += ok; F += not ok; print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))
d = tempfile.mkdtemp(); src = os.path.join(d, "site")
os.makedirs(os.path.join(src, "css", "empty")); os.makedirs(os.path.join(src, "img"))
open(os.path.join(src, "index.html"), "w").write("<h1>hi</h1>" * 100)
open(os.path.join(src, "css", "a.css"), "w").write("body{}")
open(os.path.join(src, "img", "x.bin"), "wb").write(os.urandom(300000))
open(os.path.join(src, "Ünïcode ä.txt"), "w").write("ok")
os.symlink(os.path.join(src, "css"), os.path.join(src, "linkdir"))
ref = shutil.make_archive(os.path.join(d, "ref"), "zip", src)
new = m.make_zip(os.path.join(d, "new"), src)
zr, zn = zipfile.ZipFile(ref), zipfile.ZipFile(new)
check("same entry names as make_archive", sorted(zr.namelist()) == sorted(zn.namelist()), (sorted(zr.namelist()), sorted(zn.namelist())))
check("same contents", all(zr.read(n) == zn.read(n) for n in zr.namelist()))
check("zip test OK", zn.testzip() is None)
check("returns the .zip path, no .part left", new.endswith("new.zip") and not os.path.exists(new + ".part"))
# stop flag set before: ZipStopped, nothing left
m._shutdown_requested = True
try:
    m.make_zip(os.path.join(d, "stopped"), src); ok = False
except m.ZipStopped:
    ok = True
check("stop flag: ZipStopped raised", ok)
check("stop flag: no .zip and no .part left", not os.path.exists(os.path.join(d, "stopped.zip")) and not os.path.exists(os.path.join(d, "stopped.zip.part")))
m._shutdown_requested = False
# real SIGTERM in a child during a large file
big = os.path.join(d, "big"); os.makedirs(big)
with open(os.path.join(big, "huge.bin"), "wb") as f:
    for _ in range(300): f.write(os.urandom(1024 * 1024))     # 300 MB, slow to deflate
child = textwrap.dedent('''
    import sys, types, importlib.util, time
    sys.modules["indexer"] = types.SimpleNamespace(process_dir=lambda *a: None)
    spec = importlib.util.spec_from_file_location("mmiLoader", sys.argv[1]); m = importlib.util.module_from_spec(spec)
    sys.modules["mmiLoader"] = m; spec.loader.exec_module(m)
    m.STATUS_FILE = sys.argv[3] + "/status"
    try:
        m.make_zip(sys.argv[3] + "/bigzip", sys.argv[2]); print("FINISHED")
    except m.ZipStopped:
        print("STOPPED")
''')
cf = os.path.join(d, "child.py"); open(cf, "w").write(child)
p = subprocess.Popen([sys.executable, cf, MMI, big, d], stdout=subprocess.PIPE, text=True)
time.sleep(2); t = time.time(); p.send_signal(signal.SIGTERM); out = p.communicate(timeout=60)[0]; took = time.time() - t
check("SIGTERM during a 300 MB file: stops (%.1f s)" % took, "STOPPED" in out and took < 10, out)
check("SIGTERM: no bigzip.zip and no .part left", not os.path.exists(os.path.join(d, "bigzip.zip")) and not os.path.exists(os.path.join(d, "bigzip.zip.part")))
shutil.rmtree(d)
print(f"\nResults: {P} passed, {F} failed"); sys.exit(1 if F else 0)
