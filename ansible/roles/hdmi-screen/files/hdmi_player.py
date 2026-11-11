#!/usr/bin/env python3
"""HDMI player for a Raspberry Pi ConnectBox (2026-11-11, Kirk's design).

What it shows on the HDMI screen:
  * the admin's playlist (Configuration, Advanced), looped for ever;
  * a single item a visitor (or the admin) chose with "Play on HDMI": it
    interrupts the playlist, plays once, then the playlist starts again;
  * the splash picture (hdmi_splash.py: logo, box name, Wi-Fi name) when the
    playlist is empty and nothing was chosen, and behind audio-only files.

It drives one long-running mpv (no desktop needed: mpv draws straight on the
HDMI output through DRM/KMS) over mpv's JSON IPC socket, and takes commands
from connectbox-manage over its own Unix socket, one JSON object per line:
  {"cmd": "status"}                      -> {"ok": true, "mode": ..., ...}
  {"cmd": "play", "path": "<file>"}      -> play one item now
  {"cmd": "stop"}                        -> stop everything, splash until "reload"
  {"cmd": "reload"}                      -> re-read the playlist file, re-make the
                                            splash, play the playlist from the top

Files: playlist /usr/local/connectbox/hdmi/playlist.json
       {"items": [{"path": "...", "name": "..."}], "image_seconds": 10}
       splash    /usr/local/connectbox/hdmi/splash.png
Only files under the box's content folders, with a video, audio or picture
extension, are ever played (check_media_path), so a request cannot make it
open anything else.
"""
import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time

HDMI_DIR = "/usr/local/connectbox/hdmi"
PLAYLIST_FILE = os.path.join(HDMI_DIR, "playlist.json")
SPLASH_FILE = os.path.join(HDMI_DIR, "splash.png")
SPLASH_MAKER = ["/usr/local/connectbox/battery_tool_venv/bin/python3",
                "/usr/local/connectbox/bin/hdmi_splash.py", "--out", SPLASH_FILE]
RUN_DIR = "/run/connectbox"
CONTROL_SOCKET = os.path.join(RUN_DIR, "hdmi.sock")
MPV_SOCKET = os.path.join(RUN_DIR, "hdmi-mpv.sock")
DRM_DIR = "/sys/class/drm"

# Where media may come from: the menus' media links and what they point to
CONTENT_ROOTS = ["/var/www/enhanced/content/www/assets/content", "/media"]
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".3gp", ".3g2"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".flac"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
DEFAULT_IMAGE_SECONDS = 10
RETRY_SECS = 30          # no monitor / mpv died: try again this often

log = logging.getLogger("hdmi_player")


def media_kind(path):
    """Return "video", "audio" or "image" from the file extension, else None."""
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    return None


def check_media_path(path, roots=None):
    """Return the real path of a playable file inside the content folders, else None.

    The path (and, for a menu's media link, its target) must resolve under
    one of CONTENT_ROOTS, exist as a regular file and have a media extension.
    """
    roots = roots or CONTENT_ROOTS
    if not isinstance(path, str) or not path or "\0" in path:
        return None
    real = os.path.realpath(path)
    if not any(real == r or real.startswith(os.path.realpath(r) + os.sep) for r in roots):
        return None
    if not os.path.isfile(real) or media_kind(real) is None:
        return None
    return real


def read_playlist(path=None):
    """Return (list of playable real paths, seconds per picture) from the playlist file.

    A missing or broken file is an empty playlist; items that are no longer
    on the box (key pulled out, content changed) are skipped.
    """
    try:
        with open(path or PLAYLIST_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return [], DEFAULT_IMAGE_SECONDS
    items = []
    for item in data.get("items", []) if isinstance(data, dict) else []:
        p = item.get("path") if isinstance(item, dict) else item
        real = check_media_path(p)
        if real:
            items.append(real)
    try:
        secs = max(2, min(600, int(data.get("image_seconds", DEFAULT_IMAGE_SECONDS))))
    except (TypeError, ValueError, AttributeError):
        secs = DEFAULT_IMAGE_SECONDS
    return items, secs


_LOADFILE_HAS_INDEX = None


def loadfile_has_index():
    """True when this mpv's "loadfile" takes an index before the per-file options.

    mpv 0.38 changed the command from loadfile <file> <flags> <options> to
    loadfile <file> <flags> <index> <options>.  The answer is read once from
    "mpv --version" ("mpv v0.40.0 ..." or "mpv 0.35.1 ..."); if the version
    cannot be read the newer form is assumed (Raspberry Pi OS Trixie has 0.40).
    """
    global _LOADFILE_HAS_INDEX
    if _LOADFILE_HAS_INDEX is None:
        _LOADFILE_HAS_INDEX = True
        try:
            out = subprocess.run(["mpv", "--version"], capture_output=True, text=True, timeout=20).stdout
            parts = out.split()[1].lstrip("v").split(".")
            _LOADFILE_HAS_INDEX = (int(parts[0]), int(parts[1])) >= (0, 38)
        except (OSError, subprocess.SubprocessError, IndexError, ValueError):
            pass
    return _LOADFILE_HAS_INDEX


def load_args(path, flag):
    """Return the mpv "loadfile" command for one file ("replace" or "append").

    Audio files get the splash as their picture (a per-file cover-art-files
    option), so the screen shows the box name while they play.  Video and
    picture files get no option: with the splash as cover art mpv shows it
    in place of the file's own video.
    """
    if media_kind(path) != "audio":
        return ("loadfile", path, flag)
    options = {"cover-art-files": SPLASH_FILE}
    if loadfile_has_index():
        return ("loadfile", path, flag, -1, options)
    return ("loadfile", path, flag, options)


def connected_hdmi():
    """Return (DRM connector name, ALSA card name) of the first connected HDMI port, or None.

    HDMI-A-1 is the vc4hdmi0 sound card, HDMI-A-2 vc4hdmi1 (Pi 4/5, CM4/CM5).
    """
    try:
        names = sorted(os.listdir(DRM_DIR))
    except OSError:
        return None
    for name in names:
        if "-HDMI-A-" not in name:
            continue
        try:
            with open(os.path.join(DRM_DIR, name, "status")) as f:
                if f.read().strip() != "connected":
                    continue
        except OSError:
            continue
        connector = name.split("-", 1)[1]                 # card1-HDMI-A-1 -> HDMI-A-1
        index = int(connector.rsplit("-", 1)[1]) - 1
        return connector, "vc4hdmi%d" % index
    return None


class Mpv:
    """One mpv process on the HDMI output, controlled over its JSON IPC socket."""

    def __init__(self, connector, card, on_event):
        """Start mpv idle on connector, with audio to card; on_event(dict) gets mpv events."""
        self.on_event = on_event
        self.lock = threading.Lock()
        self.request_id = 0
        try:
            os.unlink(MPV_SOCKET)
        except OSError:
            pass
        cmd = ["mpv", "--no-config", "--idle=yes", "--really-quiet", "--no-terminal",
               "--vo=gpu", "--gpu-context=drm", "--drm-connector=" + connector,
               "--hwdec=auto", "--audio-device=alsa/hdmi:CARD=%s,DEV=0" % card,
               "--keep-open=no", "--osc=no", "--osd-level=0", "--input-default-bindings=no",
               "--cover-art-auto=no", "--audio-display=external-first",
               "--input-ipc-server=" + MPV_SOCKET]
        # No --cover-art-files here: as a global option mpv added the splash to
        #  every file as an external picture track and chose it over the file's
        #  own video, so videos played with sound behind the splash picture
        #  (2026-11-11, CM5).  load_args() gives it to audio files only.
        log.info("starting mpv on %s (audio %s)", connector, card)
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)
        deadline = time.time() + 10
        while not os.path.exists(MPV_SOCKET):
            if self.proc.poll() is not None or time.time() > deadline:
                raise RuntimeError("mpv did not start (exit %s)" % self.proc.poll())
            time.sleep(0.1)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(MPV_SOCKET)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        """Read mpv's replies and events (one JSON per line) and pass events on."""
        buf = b""
        while True:
            try:
                data = self.sock.recv(65536)
            except OSError:
                data = b""
            if not data:
                self.on_event({"event": "mpv-gone"})
                return
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if "event" in msg:
                    self.on_event(msg)
                elif msg.get("error", "success") != "success":
                    # mpv refused a command (it runs --really-quiet, so this is
                    #  the only place such an error becomes visible)
                    log.warning("mpv refused command %s: %s", msg.get("request_id"), msg.get("error"))

    def command(self, *args):
        """Send one mpv command (e.g. "loadfile", path, "append"); errors are logged, not raised."""
        with self.lock:
            self.request_id += 1
            msg = {"command": list(args), "request_id": self.request_id}
            try:
                self.sock.sendall(json.dumps(msg).encode() + b"\n")
            except OSError as e:
                log.warning("mpv command %s failed: %s", args[0], e)

    def alive(self):
        """True while the mpv process is running."""
        return self.proc.poll() is None

    def close(self):
        """Stop mpv."""
        try:
            self.command("quit")
            self.proc.wait(5)
        except Exception:
            self.proc.kill()


class Player:
    """What the screen should show (playlist / chosen item / splash), applied to mpv."""

    def __init__(self):
        """Start with no mpv; run() starts it when a monitor is connected."""
        self.mpv = None
        self.lock = threading.RLock()
        self.mode = "off"            # off (no monitor), splash, stopped, playlist, single
        self.single = None           # real path of a chosen item while it plays
        # True after the admin's Stop: the splash stays up (also after a chosen
        #  item ends) until the playlist is started or saved again.  Not kept
        #  across a restart: a box that boots plays its playlist.
        self.stopped = False
        self.playlist, self.image_seconds = read_playlist()
        self.make_splash()

    # -- splash and playlist -------------------------------------------------
    def make_splash(self):
        """(Re)make the splash picture (box name and Wi-Fi name may have changed)."""
        try:
            subprocess.run(SPLASH_MAKER, timeout=60, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as e:
            log.warning("could not make the splash picture: %s", e)

    def show_playlist_or_splash(self):
        """Loop the playlist if it has items and was not stopped, else show the splash picture."""
        with self.lock:
            self.single = None
            if not self.mpv:
                return
            self.mpv.command("set_property", "image-display-duration", self.image_seconds)
            if self.playlist and not self.stopped:
                self.mode = "playlist"
                self.mpv.command("set_property", "loop-playlist", "inf")
                for i, path in enumerate(self.playlist):
                    self.mpv.command(*load_args(path, "replace" if i == 0 else "append"))
            else:
                self.mode = "stopped" if self.stopped else "splash"
                self.mpv.command("set_property", "loop-playlist", "no")
                self.mpv.command("set_property", "image-display-duration", "inf")
                self.mpv.command("loadfile", SPLASH_FILE, "replace")

    def play_single(self, real):
        """Play one chosen item now (interrupting the playlist), once."""
        with self.lock:
            if not self.mpv:
                return False
            self.mode = "single"
            self.single = real
            self.mpv.command("set_property", "loop-playlist", "no")
            self.mpv.command("set_property", "image-display-duration", self.image_seconds)
            self.mpv.command(*load_args(real, "replace"))
            return True

    def on_event(self, ev):
        """mpv event: when a chosen item has finished, go back to the playlist."""
        name = ev.get("event")
        if name == "end-file" and ev.get("reason") in ("eof", "error"):
            with self.lock:
                if self.mode == "single":
                    log.info("chosen item finished (%s): back to the playlist", ev.get("reason"))
                    threading.Thread(target=self.show_playlist_or_splash, daemon=True).start()

    # -- commands from connectbox-manage ---------------------------------------
    def handle(self, req):
        """Carry out one control request and return the reply (dict)."""
        cmd = req.get("cmd") if isinstance(req, dict) else None
        if cmd == "status":
            return {"ok": True, "mode": self.mode, "playing": self.single,
                    "playlist_items": len(self.playlist), "monitor": bool(connected_hdmi())}
        if cmd == "play":
            real = check_media_path(req.get("path"))
            if not real:
                return {"ok": False, "error": "not a playable file on this box"}
            if not self.play_single(real):
                return {"ok": False, "error": "no HDMI screen connected"}
            return {"ok": True, "mode": "single", "playing": real}
        if cmd == "stop":
            # Stop everything (a chosen item and the playlist): the splash stays
            #  up until "reload".  Before 2026-11-11 this went back to the
            #  playlist, so the admin could not stop the screen at all.
            self.stopped = True
            self.show_playlist_or_splash()
            return {"ok": True, "mode": self.mode}
        if cmd == "reload":
            # Sent when the playlist is saved (and by "Play playlist", after a
            #  "stop"): the playlist runs again from its first item, unless a
            #  chosen item is playing - then it starts when that item ends.
            self.stopped = False
            self.playlist, self.image_seconds = read_playlist()
            self.make_splash()
            if self.mode != "single":
                self.show_playlist_or_splash()
            return {"ok": True, "mode": self.mode, "playlist_items": len(self.playlist)}
        return {"ok": False, "error": "unknown command"}

    def serve_control(self):
        """Answer control requests on CONTROL_SOCKET (root only, mode 0600)."""
        try:
            os.unlink(CONTROL_SOCKET)
        except OSError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(CONTROL_SOCKET)
        os.chmod(CONTROL_SOCKET, 0o600)
        srv.listen(8)
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn):
        """One control connection: one request line in, one reply line out."""
        with conn:
            conn.settimeout(10)
            buf = b""
            try:
                while b"\n" not in buf and len(buf) < 65536:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf += data
                req = json.loads(buf.split(b"\n", 1)[0] or b"{}")
                reply = self.handle(req)
            except (OSError, ValueError) as e:
                reply = {"ok": False, "error": "bad request: %s" % e}
            try:
                conn.sendall(json.dumps(reply).encode() + b"\n")
            except OSError:
                pass

    # -- main loop ---------------------------------------------------------------
    def run(self):
        """Keep mpv running while a monitor is connected; restart it if it dies."""
        threading.Thread(target=self.serve_control, daemon=True).start()
        while True:
            port = connected_hdmi()
            with self.lock:
                if self.mpv and (not self.mpv.alive() or not port):
                    log.info("mpv stopped or monitor unplugged")
                    self.mpv.close()
                    self.mpv, self.mode = None, "off"
                if not self.mpv and port:
                    try:
                        self.mpv = Mpv(port[0], port[1], self.on_event)
                        self.show_playlist_or_splash()
                    except (OSError, RuntimeError) as e:
                        log.warning("could not start mpv: %s", e)
                        self.mpv = None
            time.sleep(RETRY_SECS if not self.mpv else 5)


def main():
    """Start the player (run by connectbox-hdmi.service)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(HDMI_DIR, exist_ok=True)
    Player().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
