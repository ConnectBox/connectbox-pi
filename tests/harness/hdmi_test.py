"""HDMI screen (Raspberry Pi, 2026-11-11): player logic, splash, page patches.

usage: python3 hdmi_test.py <connectbox-pi checkout> [connectbox-admin-ui checkout]

- hdmi_player.py: which files may be played (only video/audio/pictures in the
  content folders, symlinks followed, /etc refused), playlist reading
  (missing/broken file, gone items skipped, picture seconds 2..600), the
  connected HDMI port and its sound card, control commands with a fake mpv
  (play interrupts the playlist, a chosen item that ends returns to it,
  empty playlist -> splash, refused paths not sent to mpv);
- hdmi_splash.py: draws a 1920x1080 picture (when Pillow is installed);
- patch_admin_hdmi.py: adds the section and script once, idempotent,
  recognises a release that has it built in, fails on unknown pages; its
  embedded script and section are the same as connectbox-admin-ui's
  hdmi_admin.js and hdmi.html; the Play playlist button;
- patch_hdmi_button.py: patches a bundle with the stock download button once,
  result is valid JavaScript (node --check, if node is installed).
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, types
PI = os.path.abspath(sys.argv[1]); ADMIN = sys.argv[2] if len(sys.argv) > 2 else None
FILES = os.path.join(PI, "ansible/roles/hdmi-screen/files")
P = F = 0


def check(name, ok, detail=""):
    global P, F
    P += bool(ok); F += not ok
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else ": " + str(detail)))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(FILES, name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


T = tempfile.mkdtemp()
try:
    hp = load("hdmi_player")
    # -- media paths -----------------------------------------------------------
    content = os.path.join(T, "www/assets/content"); usb = os.path.join(T, "media/usb0")
    os.makedirs(os.path.join(content, "eng/media")); os.makedirs(usb)
    for n in ("film.mp4", "song.mp3", "pic.jpg", "doc.pdf", "old.3gp"):
        open(os.path.join(usb, n), "w").write("x")
        os.symlink(os.path.join(usb, n), os.path.join(content, "eng/media", n))
    os.symlink("/etc/passwd", os.path.join(content, "eng/media", "evil.mp4"))
    roots = [content, os.path.join(T, "media")]
    hp.CONTENT_ROOTS = roots
    link = lambda n: os.path.join(content, "eng/media", n)
    check("menu link to a video on the USB is playable", hp.check_media_path(link("film.mp4")) == os.path.join(usb, "film.mp4"))
    check("audio, picture and .3gp are playable", all(hp.check_media_path(link(n)) for n in ("song.mp3", "pic.jpg", "old.3gp")))
    check("PDF refused", hp.check_media_path(link("doc.pdf")) is None)
    check("link pointing outside the content folders refused (evil.mp4 -> /etc/passwd)", hp.check_media_path(link("evil.mp4")) is None)
    for bad in ("/etc/passwd", "/etc/shadow", link("../../../../../etc/passwd"), "", None, 5, "a\0b.mp4", link("missing.mp4")):
        check("refused: %r" % (bad,), hp.check_media_path(bad) is None)
    # -- playlist ----------------------------------------------------------------
    pl = os.path.join(T, "playlist.json")
    check("no playlist file: empty, 10 s pictures", hp.read_playlist(pl) == ([], 10))
    open(pl, "w").write("{broken")
    check("broken playlist file: empty", hp.read_playlist(pl) == ([], 10))
    json.dump({"items": [{"path": link("film.mp4")}, {"path": link("gone.mp4")}, {"path": "/etc/passwd"}, link("pic.jpg")], "image_seconds": 9999}, open(pl, "w"))
    items, secs = hp.read_playlist(pl)
    check("playlist: gone and refused items skipped, order kept", items == [os.path.join(usb, "film.mp4"), os.path.join(usb, "pic.jpg")], items)
    check("picture seconds kept at most 600", secs == 600)
    json.dump({"items": [], "image_seconds": 0}, open(pl, "w"))
    check("picture seconds at least 2", hp.read_playlist(pl)[1] == 2)
    # -- HDMI port ---------------------------------------------------------------
    drm = os.path.join(T, "drm")
    for name, st in (("card1-HDMI-A-1", "disconnected"), ("card1-HDMI-A-2", "connected"), ("card0-DSI-1", "connected")):
        os.makedirs(os.path.join(drm, name)); open(os.path.join(drm, name, "status"), "w").write(st + "\n")
    hp.DRM_DIR = drm
    check("second HDMI port connected: HDMI-A-2 with sound card vc4hdmi1", hp.connected_hdmi() == ("HDMI-A-2", "vc4hdmi1"), hp.connected_hdmi())
    open(os.path.join(drm, "card1-HDMI-A-2", "status"), "w").write("disconnected\n")
    check("no screen: None", hp.connected_hdmi() is None)
    open(os.path.join(drm, "card1-HDMI-A-1", "status"), "w").write("connected\n")
    # -- control commands with a fake mpv -----------------------------------------
    class FakeMpv:
        def __init__(self): self.cmds = []
        def command(self, *a): self.cmds.append(a)
        def alive(self): return True
    hp.SPLASH_MAKER = ["true"]; hp.PLAYLIST_FILE = pl
    # The splash is given to audio files only, as a per-file option (as a global
    #  mpv option it replaced every video's picture, 2026-11-11).  mpv >= 0.38
    #  takes an index before the options, older ones do not.
    hp._LOADFILE_HAS_INDEX = True
    cover = {"cover-art-files": hp.SPLASH_FILE}
    check("video and picture are loaded without the splash as cover art",
          hp.load_args("/x/film.mp4", "replace") == ("loadfile", "/x/film.mp4", "replace") and hp.load_args("/x/pic.jpg", "append") == ("loadfile", "/x/pic.jpg", "append"))
    check("audio is loaded with the splash as its picture (mpv 0.38+: index -1 first)", hp.load_args("/x/song.mp3", "append") == ("loadfile", "/x/song.mp3", "append", -1, cover))
    hp._LOADFILE_HAS_INDEX = False
    check("audio on mpv before 0.38: options without the index", hp.load_args("/x/song.mp3", "replace") == ("loadfile", "/x/song.mp3", "replace", cover))
    hp._LOADFILE_HAS_INDEX = True
    check("mpv is not started with a global --cover-art-files", '"--cover-art-files=' not in open(os.path.join(FILES, "hdmi_player.py"), encoding="utf-8").read().split("# No --cover-art-files")[0])
    json.dump({"items": [link("film.mp4"), link("song.mp3")], "image_seconds": 5}, open(pl, "w"))
    p = hp.Player(); p.mpv = FakeMpv(); p.show_playlist_or_splash()
    loads = [c for c in p.mpv.cmds if c[0] == "loadfile"]
    check("playlist mode: both files loaded, first replaces, loop on",
          p.mode == "playlist" and [c[1:] for c in loads] == [(os.path.join(usb, "film.mp4"), "replace"), (os.path.join(usb, "song.mp3"), "append", -1, cover)]
          and ("set_property", "loop-playlist", "inf") in p.mpv.cmds, p.mpv.cmds)
    p.mpv.cmds = []
    r = p.handle({"cmd": "play", "path": link("pic.jpg")})
    check("play: interrupts the playlist with the chosen file, no loop", r["ok"] and p.mode == "single"
          and ("loadfile", os.path.join(usb, "pic.jpg"), "replace") in p.mpv.cmds and ("set_property", "loop-playlist", "no") in p.mpv.cmds, (r, p.mpv.cmds))
    p.mpv.cmds = []
    r = p.handle({"cmd": "play", "path": "/etc/shadow"})
    check("play /etc/shadow: refused, nothing sent to mpv", not r["ok"] and p.mpv.cmds == [] and p.mode == "single", (r, p.mpv.cmds))
    import threading, time
    p.on_event({"event": "end-file", "reason": "stop"})
    time.sleep(0.2)
    check("chosen file stopped by a new load: stays on it", p.mode == "single")
    p.on_event({"event": "end-file", "reason": "eof"})
    time.sleep(0.3)
    check("chosen file finished: back to the playlist", p.mode == "playlist" and p.single is None)
    # -- Stop really stops (2026-11-11: it used to go back to the playlist) ---------
    p.mpv.cmds = []
    r = p.handle({"cmd": "stop"})
    check("stop: playlist ended, splash shown, mode stopped", r["ok"] and p.mode == "stopped"
          and ("loadfile", hp.SPLASH_FILE, "replace") in p.mpv.cmds and not any(c[0] == "loadfile" and c[1] != hp.SPLASH_FILE for c in p.mpv.cmds), (r, p.mpv.cmds))
    p.handle({"cmd": "play", "path": link("pic.jpg")}); p.on_event({"event": "end-file", "reason": "eof"}); time.sleep(0.3)
    check("stopped: a chosen file plays, then the splash again (playlist stays stopped)", p.mode == "stopped" and p.single is None, p.mode)
    r = p.handle({"cmd": "reload"})
    check("reload (playlist saved / Play playlist): playlist runs again", r["ok"] and p.mode == "playlist" and not p.stopped, r)
    json.dump({"items": []}, open(pl, "w")); p.mpv.cmds = []
    r = p.handle({"cmd": "reload"})
    check("reload with an empty playlist: splash shown for ever", r["ok"] and p.mode == "splash"
          and ("loadfile", hp.SPLASH_FILE, "replace") in p.mpv.cmds and ("set_property", "image-display-duration", "inf") in p.mpv.cmds, (r, p.mpv.cmds))
    st = p.handle({"cmd": "status"})
    check("status reports mode, monitor and playlist size", st["ok"] and st["mode"] == "splash" and st["monitor"] is True and st["playlist_items"] == 0, st)
    check("unknown command refused", p.handle({"cmd": "rm -rf"})["ok"] is False and p.handle("x")["ok"] is False)
    p.mpv = None
    check("play with no screen: clean error", p.handle({"cmd": "play", "path": link("film.mp4")}) == {"ok": False, "error": "no HDMI screen connected"})
    # -- splash --------------------------------------------------------------------
    try:
        import PIL  # noqa
        out = os.path.join(T, "splash.png")
        r = subprocess.run([sys.executable, os.path.join(FILES, "hdmi_splash.py"), "--out", out, "--name", "Test Box", "--ssid", "Test - Free Media"], capture_output=True, text=True)
        from PIL import Image
        check("splash: 1920x1080 PNG drawn", r.returncode == 0 and Image.open(out).size == (1920, 1080), r.stderr)
        check("splash: no temporary file left", not os.path.exists(out + ".tmp.png"))
    except ImportError:
        print("  [SKIP] splash (Pillow not installed)")
    # -- admin page patch ------------------------------------------------------------
    pa = load("patch_admin_hdmi")
    dist = os.path.join(T, "dist"); os.makedirs(dist)
    page = '<html><body><div id="otg">x</div><div id="system">y</div><script src="./main.bundle.js"></script><script src="./admin.bundle.js"></script></body></html>'
    open(os.path.join(dist, "index.html"), "w").write(page); open(os.path.join(dist, "admin.bundle.js"), "w").write("//")
    run = lambda d: subprocess.run([sys.executable, os.path.join(FILES, "patch_admin_hdmi.py"), d], capture_output=True, text=True)
    r = run(dist); t = open(os.path.join(dist, "index.html")).read()
    check("admin page: section before System and script after admin.bundle.js", r.returncode == 0 and t.count('id="hdmi-controls"') == 1
          and t.index('id="hdmi"') < t.index('<div id="system">') and t.index("admin.bundle.js") < t.index("hdmi_admin.js")
          and os.path.exists(os.path.join(dist, "hdmi_admin.js")), r.stdout)
    r = run(dist)
    check("admin page: second run changes nothing", r.returncode == 0 and open(os.path.join(dist, "index.html")).read() == t and "already" in r.stdout, r.stdout)
    open(os.path.join(dist, "index.html"), "w").write(page.replace('<div id="system">', '<div id="hdmi-controls"></div><div id="system">'))
    r = run(dist)
    check("admin page: release with the section built in is left alone", r.returncode == 0 and "built into this release" in r.stdout, r.stdout)
    open(os.path.join(dist, "index.html"), "w").write("<html>other</html>")
    check("admin page: unknown page -> exit 1, unchanged", run(dist).returncode == 1 and open(os.path.join(dist, "index.html")).read() == "<html>other</html>")
    # Language made visible (Kirk, 2026-11-13): chooser groups "Language: xxx",
    #  playlist entries "name (kind) . Language: " + the language underlined
    check("chooser group headings read 'Language: xxx'", "groups[m.lang].label = 'Language: ' + m.lang;" in pa.JS)
    check("playlist entries: 'Language: ' then the language in <u>",
          "Language: '));" in pa.JS and "document.createElement('u')" in pa.JS and "u.textContent = media[i].lang;" in pa.JS)
    if ADMIN:
        src = os.path.join(ADMIN, "src/js/admin/hdmi_admin.js")
        check("embedded script == connectbox-admin-ui hdmi_admin.js", os.path.exists(src) and open(src, encoding="utf-8").read() == pa.JS, src)
        sec = os.path.join(ADMIN, "src/templates/parts/admin/sections/hdmi.html")
        check("embedded section == connectbox-admin-ui hdmi.html", os.path.exists(sec)
              and '<div class="hidden isAdvanced" id="hdmi">' + open(sec, encoding="utf-8").read().strip() + '</div>' == pa.SECTION, sec)
    # "Play playlist" (2026-11-11): in the section, and added by the script on a
    #  page patched before the button existed (only the script is refreshed there)
    check("admin page: Play playlist button in the section", pa.SECTION.count('id="hdmi-play-list"') == 1)
    check("admin page: script adds Play playlist when the page lacks it, saves then starts the playlist",
          "playList.id = 'hdmi-play-list'" in pa.JS and "insertBefore(playList, el('hdmi-stop'))" in pa.JS
          and "playList.onclick = function () {\n      request('GET', 'hdmi/stop'" in pa.JS
          and pa.JS.index("playList.onclick") < pa.JS.index("savePlaylist(function () {\n          say(playlist.length"))
    # -- media page button patch -----------------------------------------------------
    pb = load("patch_hdmi_button")
    build = os.path.join(T, "build"); os.makedirs(build)
    bundle = ("var DownloadButtonComponent = (function () {\n    function DownloadButtonComponent() {}\n"
              + pb.METHOD_ANCHOR + "\n        return 1;\n    };\n"
              "    DownloadButtonComponent.decorators = [{ template: '<button ion-button clear icon-only " + pb.TEMPLATE_ANCHOR + "' }];\n"
              "    return DownloadButtonComponent;\n}());\n")
    open(os.path.join(build, "0.js"), "w").write(bundle); open(os.path.join(build, "2.js"), "w").write("var other = 1;\n")
    runb = lambda: subprocess.run([sys.executable, os.path.join(FILES, "patch_hdmi_button.py"), build], capture_output=True, text=True)
    r = runb(); t = open(os.path.join(build, "0.js")).read()
    check("button: bundle patched once (methods + button), other bundle untouched",
          r.returncode == 0 and t.count(pb.MARKER) == 1 and t.count('(click)="cbHdmiPlay()"') == 1 and open(os.path.join(build, "2.js")).read() == "var other = 1;\n", r.stdout)
    r = runb()
    check("button: second run changes nothing", r.returncode == 0 and open(os.path.join(build, "0.js")).read() == t)
    if shutil.which("node"):
        n = subprocess.run(["node", "--check", os.path.join(build, "0.js")], capture_output=True, text=True)
        check("button: patched bundle is valid JavaScript", n.returncode == 0, n.stderr)
    os.remove(os.path.join(build, "0.js"))
    check("button: no bundle with the stock button -> exit 1", runb().returncode == 1)
finally:
    shutil.rmtree(T, ignore_errors=True)
print("\nResults: %d passed, %d failed" % (P, F)); sys.exit(1 if F else 0)
