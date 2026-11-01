import os, sys, types, tempfile, importlib.util
stub = types.ModuleType("indexer"); stub.process_dir = lambda *a: None; sys.modules["indexer"] = stub
spec = importlib.util.spec_from_file_location("mmiLoader", sys.argv[1]); m = importlib.util.module_from_spec(spec)
sys.modules["mmiLoader"] = m; spec.loader.exec_module(m)
m.STATUS_FILE = tempfile.mktemp()
P = F = 0
def check(l, c, d=""):
    global P, F
    if c: P += 1; print("  [PASS]", l)
    else: F += 1; print("  [FAIL]", l, d)
def run(flag=None, existing=False):
    d = tempfile.mkdtemp(); media = d + "/content"; out = d + "/www"
    site = media + "/en/Site"; os.makedirs(site); os.makedirs(out + "/en/html")
    open(site + "/index.html", "w").write("<html>hi</html>"); open(site + "/v.mp4", "wb").write(b"x" * 1000)
    if flag: open(media + "/" + flag, "w").close()
    zipname = media + "/.webarchive-en-en-Site.zip"
    if existing: open(zipname, "w").write("old")
    r = m.handle_web_content(site, "Site", "en", [], ["index.html", "v.mp4"], out, media, [], "collection", 0)
    link = out + "/en/html/Site.zip"
    return os.path.exists(zipname), os.path.lexists(link), os.path.exists(link), r, zipname
z, l, ok, r, _ = run()
check("no flag: no zip made", not z)
check("no flag: no (dangling) zip link", not l)
check("no flag: still web content", r[0] == "html" and r[1])
z, l, ok, r, _ = run(".webcompress")
check(".webcompress: zip made and linked", z and l and ok)
z, l, ok, r, _ = run(".WebCompress")
check(".WebCompress (any case): zip made", z and ok)
z, l, ok, r, zn = run(None, existing=True)
check("zip from an earlier run is linked and kept", z and ok and open(zn).read() == "old")
z, l, ok, r, _ = run(".NoWebcompress")
check(".NoWebcompress alone: no zip (now ignored, same as no flag)", not z and not l)
print("Results: %d passed, %d failed" % (P, F))
