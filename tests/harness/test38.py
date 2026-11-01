"""Fix 38: stale front-panel status file (/tmp/creating_menus.txt).

usage: python3 test38.py <new mmiLoader.py> <old mmiLoader.py> <new hats.py>
"""
import ast, os, subprocess, sys, tempfile, textwrap, time, types, logging

NEW_MMI, OLD_MMI, HATS = sys.argv[1:4]
PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print("  [PASS] " + label)
    else:
        FAIL += 1; print("  [FAIL] " + label + ((": " + str(detail)) if detail else ""))


# ── mmiLoader: runs in a child process (real module, real SIGTERM, real atexit)
CHILD = textwrap.dedent(r'''
    import os, signal, sys, types, importlib.util
    path, status, scenario = sys.argv[1:4]
    stub = types.ModuleType("indexer"); stub.process_dir = lambda *a: None
    sys.modules["indexer"] = stub
    spec = importlib.util.spec_from_file_location("mmiLoader", path)
    m = importlib.util.module_from_spec(spec); sys.modules["mmiLoader"] = m
    spec.loader.exec_module(m)
    if hasattr(m, "STATUS_FILE"):
        m.STATUS_FILE = status
    def exists(): return "yes" if os.path.exists(status) else "no"
    if scenario == "sigterm":
        # a copy stops the loader mid-run; the run carries on briefly and
        # writes its status again before it notices the USB is gone
        m.update_display("Indexing USB")
        os.kill(os.getpid(), signal.SIGTERM)
        print("after SIGTERM:", exists())
        m.update_display("Indexing USB")
        print("after next write:", exists())
        sys.exit(0)
    if scenario == "exit":
        m.update_display("Indexing USB"); sys.exit(1)
    if scenario == "error":
        m.update_display("Indexing USB"); raise RuntimeError("boom")
    if scenario == "other_writer":
        m.update_display("Indexing USB")
        open(status, "w").write("Copying 50%")
        sys.exit(0)
    if scenario == "never_wrote":
        sys.exit(0)
    if scenario == "progress":
        m._indexing.update(total=200, done=0)
        for i in range(3):
            m._indexing["done"] = i
            m.update_display(m.processing_message("f", "en"))
        print("during run:", open(status).read().replace("\n", "|"))
        sys.exit(0)
''')


def run_child(mmi, scenario, status, pre=None):
    if pre is not None:
        open(status, "w").write(pre)
    elif os.path.exists(status):
        os.remove(status)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(CHILD)
    p = subprocess.run([sys.executable, f.name, mmi, status, scenario],
                       capture_output=True, text=True, timeout=60)
    os.remove(f.name)
    left = open(status).read() if os.path.exists(status) else None
    return p, left


print("== mmiLoader: status file after the run ends ==")
with tempfile.TemporaryDirectory() as d:
    st = os.path.join(d, "creating_menus.txt")
    p, left = run_child(NEW_MMI, "sigterm", st)
    check("SIGTERM removes the status file", "after SIGTERM: no" in p.stdout, p.stdout + p.stderr[-300:])
    check("nothing written after SIGTERM", "after next write: no" in p.stdout, p.stdout)
    check("no status file once the stopped run has exited", left is None, left)
    p, left = run_child(NEW_MMI, "exit", st)
    check("early exit (sys.exit) removes its status file", left is None, (left, p.stderr[-300:]))
    p, left = run_child(NEW_MMI, "error", st)
    check("exit on an exception removes its status file", left is None and "boom" in p.stderr, left)
    p, left = run_child(NEW_MMI, "other_writer", st)
    check("a status file someone else rewrote is left alone", left == "Copying 50%", left)
    p, left = run_child(NEW_MMI, "never_wrote", st, pre="Indexing USB")
    check("a run that wrote nothing (e.g. 'another loader running') leaves the file", left == "Indexing USB", left)
    p, left = run_child(NEW_MMI, "progress", st)
    check("progress still written during a run", "during run: Indexing 1%|of 200 files" in p.stdout, p.stdout + p.stderr[-300:])

print("== old mmiLoader (reproduces .200) ==")
real = "/tmp/creating_menus.txt"         # old code always writes here
if os.path.exists(real):
    os.remove(real)
p, _ = run_child(OLD_MMI, "sigterm", real + ".unused")
left = open(real).read() if os.path.exists(real) else None
check("old code: SIGTERM then a status write leaves 'Indexing USB' behind", left is not None and "Indexing" in left, (left, p.stdout))
if os.path.exists(real):
    os.remove(real)


# ── front panel: BasePhysicalHAT.statusFileStale / indexingStep ─────────────
print("== front panel: stale status file ==")
tree = ast.parse(open(HATS).read())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BasePhysicalHAT")
wanted = {"mmiLoaderRunning", "statusFileStale", "indexingStep", "usbCheckText"}
body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
body += [n for n in cls.body if isinstance(n, ast.Assign) and
         any(getattr(t, "id", "") in ("STATUS_STALE_SECS", "STATUS_CHECK_SECS", "_statusCheckedAt") for t in n.targets)]
check("hats.py defines the methods", len([b for b in body if isinstance(b, ast.FunctionDef)]) == 4)

with tempfile.TemporaryDirectory() as d:
    st = os.path.join(d, "creating_menus.txt")
    g = types.SimpleNamespace(a="")
    ns = {"os": os, "time": time, "logging": logging, "globals": g, "comsFileName": st,
          "usbCheckFileName": os.path.join(d, "no-usbcheck.txt"),
          "subprocess": subprocess}
    klass = type("H", (), {})
    for n in body:
        mod = ast.Module(body=[n], type_ignores=[])
        exec(compile(mod, HATS, "exec"), ns)
        if isinstance(n, ast.FunctionDef):
            fn = ns[n.name]
            deco = [getattr(x, "id", "") for x in n.decorator_list]
            setattr(klass, n.name, staticmethod(fn) if "staticmethod" in deco else fn)
        else:
            for t in n.targets:
                setattr(klass, t.id, ns[t.id])

    shown = []
    disp = types.SimpleNamespace(showWaitPage=lambda t: shown.append(("wait", t)),
                                 showSuccessPage=lambda: shown.append(("success",)))

    def new_hat(loader_running=False):
        h = klass(); h.display = disp; h.indexPending = False
        h.loaderRunning = lambda: loader_running
        return h

    def write(text, age):
        open(st, "w").write(text)
        t = time.time() - age; os.utime(st, (t, t))

    # stale: old file, no mmiLoader process
    write("Indexing USB", 600); shown.clear(); h = new_hat()
    r = h.indexingStep(False)
    check("stale file (10 min old, no mmiLoader) is removed", not os.path.exists(st))
    check("... and no wait page is shown", shown == [] and r is False, (shown, r))

    # fresh file: an index that has just written it
    write("Indexing 3%\nof 200 files", 2); shown.clear(); h = new_hat()
    r = h.indexingStep(False)
    check("fresh file (2 s old) is kept and shown", os.path.exists(st) and shown and shown[0][0] == "wait" and r is True, shown)

    # old file but mmiLoader running (one big file taking minutes)
    with tempfile.TemporaryDirectory() as pd:
        fake = os.path.join(pd, "mmiLoader.py")
        open(fake, "w").write("import time\ntime.sleep(30)\n")
        for extra in ([], ["--clear"]):
            proc = subprocess.Popen([sys.executable, fake] + extra)
            time.sleep(0.5)
            write("Indexing 40%\nof 200 files", 600); shown.clear(); h = new_hat()
            r = h.indexingStep(False)
            check("old file kept while mmiLoader.py %sis running" % (" ".join(extra) + " " if extra else ""),
                  os.path.exists(st) and shown and shown[0][0] == "wait", shown)
            proc.kill(); proc.wait()

    # check is rate-limited: right after a check, a stale file waits for the next one
    write("Indexing USB", 600); shown.clear(); h = new_hat()
    h._statusCheckedAt = time.time()
    h.indexingStep(False)
    check("within STATUS_CHECK_SECS of the last check the file is not re-checked", os.path.exists(st))
    h._statusCheckedAt = time.time() - h.STATUS_CHECK_SECS - 1
    shown.clear(); r = h.indexingStep(False)
    check("... and is removed at the next check", not os.path.exists(st) and shown == [], shown)

    # an admin command's re-index: stale file removed, then ONE success page when the loader is done
    write("Indexing USB", 600); shown.clear(); h = new_hat(loader_running=False); h.indexPending = True
    r = h.indexingStep(False)
    check("pending re-index with a stale file: one success page", shown == [("success",)] and r is False, (shown, r))

    # scan cost
    h = new_hat(); t = time.time()
    for _ in range(20):
        h.mmiLoaderRunning()
    check("mmiLoaderRunning scan is quick (%.1f ms)" % ((time.time() - t) * 50), (time.time() - t) / 20 < 0.2)

print("\nResults: %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
