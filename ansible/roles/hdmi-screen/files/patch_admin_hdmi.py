#!/usr/bin/env python3
"""
"HDMI Screen" section on the Configuration page (connectbox-admin-ui release
bundles), Raspberry Pi ConnectBox, 2026-11-11.

An Advanced option (shown after "Advanced"), placed before the System
section: the playlist looped on the HDMI screen (built from the box's video,
audio and picture files), Play now / Stop, seconds per picture, and the
switch that lets visitors use "Play on HDMI" (brand.j2 hdmi_visitor_play).
Its script is hdmi_admin.js (copied next to admin.bundle.js and loaded after
it); it talks to connectbox-manage's /admin/api/hdmi endpoints.

The same section is in connectbox-admin-ui source (hdmi.pug, admin.js imports
src/js/admin/hdmi_admin.js); a release built from that source already has it,
and this script then changes nothing.

Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_admin_hdmi.py [admin dist directory]
"""
import os
import sys

DEFAULT_DIR = '/var/www/enhanced/admin/dist'
MARKER = 'ConnectBox: HDMI screen section'
HTML_ANCHOR = '<div id="system">'
SCRIPT_ANCHOR = '<script src="./admin.bundle.js"></script>'
SCRIPT_TAG = '<script src="./hdmi_admin.js"></script>'
BUILT_IN = 'id="hdmi-controls"'
# The section's markup and script are embedded at the end of this file (the
#  Ansible "script" module copies only this file).  JS must stay the same as
#  connectbox-admin-ui src/js/admin/hdmi_admin.js (tests/harness/hdmi_test.py checks).


def write_like(path, text, like=None):
    """Write text to path atomically, keeping the mode/owner of like (or path)."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    ref = like or path
    if os.path.exists(ref):
        st = os.stat(ref)
        os.chmod(tmp, st.st_mode & 0o7777)
        try:
            os.chown(tmp, st.st_uid, st.st_gid)
        except OSError:
            pass
    os.replace(tmp, path)


def patch(d, section, js):
    """Add the section and its script to the release in d; True when done or not needed."""
    index = os.path.join(d, 'index.html')
    with open(index, 'r', encoding='utf-8') as f:
        text = f.read()
    if BUILT_IN in text and MARKER not in text:
        print(index + ': built into this release, unchanged')
        return True
    # The script file is (re)written every time, so a newer hdmi_admin.js reaches the box
    write_like(os.path.join(d, 'hdmi_admin.js'), js, like=os.path.join(d, 'admin.bundle.js'))
    if MARKER in text:
        print(index + ': already patched (hdmi_admin.js refreshed)')
        return True
    if text.count(HTML_ANCHOR) != 1 or text.count(SCRIPT_ANCHOR) != 1:
        print(index + ': expected text not found, unchanged')
        return False
    text = text.replace(HTML_ANCHOR, '<!-- ' + MARKER + ' -->' + section.strip() + HTML_ANCHOR)
    text = text.replace(SCRIPT_ANCHOR, SCRIPT_ANCHOR + SCRIPT_TAG)
    write_like(index, text)
    print(index + ': patched')
    return True


def main():
    """Patch the admin dist directory given on the command line (default: the box's)."""
    d = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    return 0 if patch(d, SECTION, JS) else 1


SECTION = '<div class="hidden isAdvanced" id="hdmi"><div class="rounded-3 bg-white mx-2 my-3 elevation-1"><div class="p-2 bg-secondary rounded-top"><h2 class="px-3 m-0 text-dark"><svg class="bi" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 16 16"><path d="M2.5 13.5A.5.5 0 0 1 3 13h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zM13.991 3l.024.001a1.46 1.46 0 0 1 .538.143.757.757 0 0 1 .302.254c.067.1.145.277.145.602v5.991l-.001.024a1.464 1.464 0 0 1-.143.538.758.758 0 0 1-.254.302c-.1.067-.277.145-.602.145H2.009l-.024-.001a1.464 1.464 0 0 1-.538-.143.758.758 0 0 1-.302-.254C1.078 10.502 1 10.325 1 10V4.009l.001-.024a1.46 1.46 0 0 1 .143-.538.758.758 0 0 1 .254-.302C1.498 3.078 1.675 3 2 3h11.991zM14 2H2C0 2 0 4 0 4v6c0 2 2 2 2 2h12c2 0 2-2 2-2V4c0-2-2-2-2-2z"></path></svg>HDMI Screen</h2></div><div class="p-4"><p class="text-caption">What the screen on the box\'s HDMI port shows: this playlist, looped. A file chosen with Play now (or by a visitor with "Play on HDMI", if allowed) plays once, then the playlist starts again. Play playlist saves the list and starts it from the top. With an empty playlist the screen shows the box name and the Wi-Fi name.</p><p class="mb-3" id="hdmi-status">Checking the HDMI player...</p><div id="hdmi-controls"><p class="mb-1">Playlist</p><ol class="mb-3" id="hdmi-playlist"></ol><div class="mb-2"><select class="form-select w-100" id="hdmi-media" aria-label="File on the box"></select></div><div class="mb-3"><button class="bg-transparent border-0 text-primary p-0 me-3" id="hdmi-add" type="button">Add to playlist</button><button class="bg-transparent border-0 text-primary p-0 me-3" id="hdmi-play" type="button">Play now</button><button class="bg-transparent border-0 text-primary p-0 me-3" id="hdmi-play-list" type="button">Play playlist</button><button class="bg-transparent border-0 text-primary p-0" id="hdmi-stop" type="button">Stop</button></div><div class="mb-3"><label for="hdmi-image-seconds">Seconds per picture </label> <input id="hdmi-image-seconds" type="number" min="2" max="600" value="10" style="width:5em"></div><button class="bg-transparent border-0 text-primary p-0" id="hdmi-save" type="button">Save playlist</button><div class="mt-3"><label><input id="hdmi_visitor_play-input" type="checkbox"> Visitors can use "Play on HDMI" on the media pages</label></div><p class="mt-2 mb-0" id="hdmi-message"></p></div></div></div></div>'

JS = '/**\n * @fileoverview "HDMI Screen" section of the Configuration page (Raspberry Pi\n * ConnectBox, 2026-11-11).  Plain ES5 with XMLHttpRequest so it runs on old\n * phones, and self-contained so the same file serves both ways:\n *  - connectbox-admin-ui source: imported by admin.js (bundled);\n *  - an existing release: copied next to admin.bundle.js and loaded with a\n *    <script> tag by connectbox-pi\'s patch_admin_hdmi.py.\n * Keep the two copies (connectbox-admin-ui src/js/admin/hdmi_admin.js and\n * connectbox-pi roles/enhanced-content/files/hdmi_admin.js) the same.\n *\n * The section (#hdmi, an Advanced option) lets the admin:\n *  - build the playlist looped on the HDMI screen from the box\'s video,\n *    audio and picture files (add, move up/down, remove, seconds per\n *    picture, Save);\n *  - play one file now, or stop it (back to the playlist);\n *  - save the playlist and start it from the top (Play playlist);\n *  - allow visitors to use "Play on HDMI" on the media pages\n *    (brand.j2 hdmi_visitor_play).\n * API: connectbox-manage src/hdmi.js (/admin/api/hdmi/...).  On a box without\n * the HDMI player the section says so and offers nothing else.\n */\n(function () {\n  \'use strict\';\n  var API = \'/admin/api/\';\n\n  /** Send a request; done(status, parsed JSON or null). 401 goes to the login page. */\n  function request(method, url, body, done) {\n    var x = new XMLHttpRequest();\n    x.open(method, API + url, true);\n    x.onload = function () {\n      if (x.status === 401) { window.location.href = \'/admin/login.html\'; return; }\n      var data = null;\n      try { data = JSON.parse(x.responseText); } catch (e) { data = null; }\n      done(x.status, data);\n    };\n    x.onerror = function () { done(0, null); };\n    if (body !== undefined) {\n      x.setRequestHeader(\'Content-Type\', \'application/json\');\n      x.send(JSON.stringify(body));\n    } else {\n      x.send();\n    }\n  }\n\n  function el(id) { return document.getElementById(id); }\n\n  /** Short message under the section\'s buttons (green ok, red error). */\n  function say(text, bad) {\n    var m = el(\'hdmi-message\');\n    if (!m) return;\n    m.textContent = text || \'\';\n    m.style.color = bad ? \'#c62828\' : \'#2e7d32\';\n  }\n\n  var media = [];        // playable files on the box: {path, name, lang, kind}\n  var playlist = [];     // web paths in order\n\n  /** Label for a file: name (language, kind). */\n  function label(path) {\n    for (var i = 0; i < media.length; i++) {\n      if (media[i].path === path) return media[i].name + \' (\' + media[i].lang + \', \' + media[i].kind + \')\';\n    }\n    return path.split(\'/\').pop() + \' (not on the box now)\';\n  }\n\n  /** Redraw the playlist with Up / Down / Remove buttons. */\n  function drawPlaylist() {\n    var list = el(\'hdmi-playlist\');\n    if (!list) return;\n    while (list.firstChild) list.removeChild(list.firstChild);\n    if (!playlist.length) {\n      var li0 = document.createElement(\'li\');\n      li0.textContent = \'Empty: the screen shows the box name and Wi-Fi name.\';\n      li0.style.listStyle = \'none\';\n      list.appendChild(li0);\n    }\n    for (var i = 0; i < playlist.length; i++) {\n      (function (i) {\n        var li = document.createElement(\'li\');\n        li.className = \'mb-1\';\n        li.appendChild(document.createTextNode(label(playlist[i]) + \' \'));\n        [[\'↑\', \'Move up\', function () { if (i > 0) { var t = playlist[i - 1]; playlist[i - 1] = playlist[i]; playlist[i] = t; } }],\n         [\'↓\', \'Move down\', function () { if (i < playlist.length - 1) { var t = playlist[i + 1]; playlist[i + 1] = playlist[i]; playlist[i] = t; } }],\n         [\'✕\', \'Remove\', function () { playlist.splice(i, 1); }]].forEach(function (b) {\n          var btn = document.createElement(\'button\');\n          btn.type = \'button\';\n          btn.className = \'bg-transparent border-0 text-primary px-1\';\n          btn.title = b[1];\n          btn.setAttribute(\'aria-label\', b[1]);\n          btn.textContent = b[0];\n          btn.onclick = function () { b[2](); drawPlaylist(); say(\'Not saved yet\'); };\n          li.appendChild(btn);\n        });\n        list.appendChild(li);\n      })(i);\n    }\n  }\n\n  /** Fill the file chooser, grouped by language. */\n  function drawMedia() {\n    var sel = el(\'hdmi-media\');\n    if (!sel) return;\n    while (sel.firstChild) sel.removeChild(sel.firstChild);\n    var groups = {};\n    for (var i = 0; i < media.length; i++) {\n      var m = media[i];\n      if (!groups[m.lang]) {\n        groups[m.lang] = document.createElement(\'optgroup\');\n        groups[m.lang].label = m.lang;\n        sel.appendChild(groups[m.lang]);\n      }\n      var o = document.createElement(\'option\');\n      o.value = m.path;\n      o.textContent = m.name + \' (\' + m.kind + \')\';\n      groups[m.lang].appendChild(o);\n    }\n    if (!media.length) {\n      var none = document.createElement(\'option\');\n      none.textContent = \'No video, audio or pictures on the box\';\n      none.value = \'\';\n      sel.appendChild(none);\n    }\n  }\n\n  /** Show the screen status line. */\n  function showStatus() {\n    request(\'GET\', \'hdmi/status\', undefined, function (code, st) {\n      var s = el(\'hdmi-status\');\n      if (!s) return;\n      if (code !== 200 || !st || st.ok === false) {\n        s.textContent = \'HDMI player not running on this box.\';\n        return;\n      }\n      var what = st.mode === \'single\' ? \'playing a chosen file\' :\n        st.mode === \'playlist\' ? \'looping the playlist\' :\n        st.mode === \'splash\' ? \'showing the box name and Wi-Fi name\' : \'no screen connected\';\n      s.textContent = (st.monitor ? \'Screen connected: \' : \'No screen connected. \') + (st.monitor ? what : \'\');\n      var v = el(\'hdmi_visitor_play-input\');\n      if (v) v.checked = !!st.visitor_play;\n    });\n  }\n\n  /** Load everything from the box. */\n  function load() {\n    if (!el(\'hdmi\')) return;\n    request(\'GET\', \'hdmi/status\', undefined, function (code, st) {\n      var body = el(\'hdmi-controls\');\n      if (code !== 200 || !st || st.error === \'HDMI player is not running\') {\n        if (body) body.style.display = \'none\';\n        var s = el(\'hdmi-status\');\n        if (s) s.textContent = \'This box has no HDMI player (Raspberry Pi builds only).\';\n        return;\n      }\n      if (body) body.style.display = \'\';\n      request(\'GET\', \'hdmi/media\', undefined, function (c1, m) {\n        media = (c1 === 200 && m && m.length !== undefined) ? m : [];\n        drawMedia();\n        request(\'GET\', \'hdmi/playlist\', undefined, function (c2, p) {\n          playlist = [];\n          if (c2 === 200 && p && p.items) {\n            for (var i = 0; i < p.items.length; i++) playlist.push(p.items[i].path);\n            if (el(\'hdmi-image-seconds\')) el(\'hdmi-image-seconds\').value = p.image_seconds || 10;\n          }\n          drawPlaylist();\n          showStatus();\n        });\n      });\n    });\n  }\n\n  /**\n   * Save the playlist as shown on the page (order and seconds per picture) to\n   * the box; the player re-reads it.  saved() runs after a successful save; a\n   * failure is reported in the message line and saved() is not called.\n   */\n  function savePlaylist(saved) {\n    var secs = parseInt(el(\'hdmi-image-seconds\').value, 10) || 10;\n    request(\'PUT\', \'hdmi/playlist\', {items: playlist, image_seconds: secs}, function (code, r) {\n      if (code === 200) saved();\n      else say(\'Save failed: \' + (r && r.error || code), true);\n    });\n  }\n\n  /** Wire the buttons and the visitor switch. */\n  function attach() {\n    if (!el(\'hdmi\')) return;\n    el(\'hdmi-add\').onclick = function () {\n      var v = el(\'hdmi-media\').value;\n      if (v) { playlist.push(v); drawPlaylist(); say(\'Not saved yet\'); }\n    };\n    el(\'hdmi-save\').onclick = function () {\n      savePlaylist(function () { say(\'Playlist saved\'); showStatus(); });\n    };\n    // "Play playlist": a page patched before this button existed keeps its old\n    // markup (only this script is refreshed), so the button is added here if missing.\n    var playList = el(\'hdmi-play-list\');\n    if (!playList) {\n      playList = document.createElement(\'button\');\n      playList.type = \'button\';\n      playList.id = \'hdmi-play-list\';\n      playList.className = \'bg-transparent border-0 text-primary p-0 me-3\';\n      playList.textContent = \'Play playlist\';\n      el(\'hdmi-stop\').parentNode.insertBefore(playList, el(\'hdmi-stop\'));\n    }\n    // Save the list as shown, then start it from its first item.  Saving alone\n    // does not interrupt a file chosen with Play now; "stop" does, and sends\n    // the player back to the playlist (or the splash when the list is empty).\n    playList.onclick = function () {\n      savePlaylist(function () {\n        request(\'GET\', \'hdmi/stop\', undefined, function (code) {\n          if (code !== 200) say(\'Could not start the playlist\', true);\n          else say(playlist.length ? \'Playing the playlist\' : \'The playlist is empty\');\n          showStatus();\n        });\n      });\n    };\n    el(\'hdmi-play\').onclick = function () {\n      var v = el(\'hdmi-media\').value;\n      if (!v) return;\n      request(\'PUT\', \'hdmi/public/play\', {path: v}, function (code, r) {\n        if (code === 200) { say(\'Playing on the screen\'); showStatus(); }\n        else say(\'Play failed: \' + (r && r.error || code), true);\n      });\n    };\n    el(\'hdmi-stop\').onclick = function () {\n      request(\'GET\', \'hdmi/stop\', undefined, function (code) {\n        say(code === 200 ? \'Back to the playlist\' : \'Stop failed\', code !== 200);\n        showStatus();\n      });\n    };\n    el(\'hdmi_visitor_play-input\').onchange = function () {\n      var on = this.checked ? 1 : 0;\n      request(\'PUT\', \'brand\', {value: \'hdmi_visitor_play=\' + on}, function (code) {\n        say(code === 200 ? (on ? \'Visitors can use Play on HDMI\' : \'Only the admin can use Play on HDMI\') : \'Save failed\', code !== 200);\n      });\n    };\n  }\n\n  function start() { attach(); load(); }\n  if (document.readyState === \'loading\') document.addEventListener(\'DOMContentLoaded\', start);\n  else start();\n})();\n'


if __name__ == '__main__':
    sys.exit(main())
