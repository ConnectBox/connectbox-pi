#!/usr/bin/env python3
"""
"Play on HDMI" button next to every download button (build/*.js), for a
Raspberry Pi ConnectBox with a screen on its HDMI port (2026-11-11).

The download button component (DownloadButtonComponent) is compiled into the
media detail page and each viewer, so every bundle that contains it is
patched, like patch_download_size.py:

  - cbHdmiOk(): true for a video, audio or picture file when the box says an
    HDMI screen is there and visitors may use it (GET
    /admin/api/hdmi/public/status, asked at most once a minute per page and
    shared by all buttons; for a logged-in admin it is always allowed);
  - cbHdmiPlay(): asks the box to play the file on the screen (PUT
    /admin/api/hdmi/public/play) and shows a tick or a cross for 3 seconds;
  - the template gets a screen-icon button after the download button, shown
    only while cbHdmiOk() is true, and the tick/cross label.

On a box without the HDMI player (NanoPi NEO, or a Pi with no screen) the
status request fails or says "not available", and no button appears.
Language-neutral (icon, tick, cross).  Plain ES5 + XMLHttpRequest so it runs
on iOS 9 / Android 4 browsers; zone.js notices the callbacks and redraws.

Idempotent.  Exits non-zero if no bundle contains the stock button.

Usage: patch_hdmi_button.py [path/to/build]
"""
import glob
import os
import sys

DEFAULT_BUILD = '/var/www/enhanced/content/www/build'
MARKER = 'DownloadButtonComponent.prototype.cbHdmiPlay'

# Inside the bundles the template is a JavaScript string literal: quotes are \'
# and line breaks the two characters \n.
TEMPLATE_ANCHOR = ('(click)="downloadFile()" [hidden]="isDownloading">\\n'
                   '  <ion-icon name="download"></ion-icon>\\n</button>\\n')
TEMPLATE_ADD = ('<button ion-button clear icon-only [ngClass]="inNavBar ? \\\'bar-button\\\' : \\\'\\\'"'
                ' [color]="inNavBar ? \\\'light\\\' : \\\'primary\\\'" (click)="cbHdmiPlay()"'
                ' [hidden]="!cbHdmiOk()" title="Play on HDMI" aria-label="Play on HDMI">\\n'
                '  <ion-icon name="desktop"></ion-icon>\\n</button>\\n'
                '<span class="cb-hdmi" [hidden]="!cbHdmiMsg" [style.color]="inNavBar ? \\\'#fff\\\' : \\\'\\\'"'
                ' style="font-size:15px;vertical-align:middle;">{{ cbHdmiMsg }}</span>\\n')

METHOD_ANCHOR = '    DownloadButtonComponent.prototype.downloadFile = function () {'
METHODS = r'''    /**
     * ConnectBox: show "Play on HDMI" for a video, audio or picture file when
     * the box has an HDMI screen that visitors may use (status shared by all
     * buttons, asked at most once a minute).
     */
    DownloadButtonComponent.prototype.cbHdmiOk = function () {
        var path = String(this.filePath || '').split('?')[0];
        if (!/\.(mp4|m4v|mov|mkv|webm|3gp|3g2|mp3|m4a|aac|ogg|oga|opus|wav|flac|jpe?g|png|gif|webp|bmp)$/i.test(path)) { return false; }
        var w = window, now = new Date().getTime();
        if (!w.cbHdmi || (now - w.cbHdmi.t > 60000)) {
            w.cbHdmi = { t: now, ok: !!(w.cbHdmi && w.cbHdmi.ok) };
            try {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/admin/api/hdmi/public/status', true);
                xhr.onreadystatechange = function () {
                    if (xhr.readyState !== 4) { return; }
                    try { var s = JSON.parse(xhr.responseText); w.cbHdmi.ok = !!(s && s.available && s.visitor_play); }
                    catch (e) { w.cbHdmi.ok = false; }
                };
                xhr.send();
            } catch (e) { }
        }
        return w.cbHdmi.ok;
    };
    /** ConnectBox: play this file on the box's HDMI screen. */
    DownloadButtonComponent.prototype.cbHdmiPlay = function () {
        var _this = this;
        this.cbHdmiMsg = '…';
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('PUT', '/admin/api/hdmi/public/play', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onreadystatechange = function () {
                if (xhr.readyState !== 4) { return; }
                _this.cbHdmiMsg = (xhr.status === 200) ? '✔' : '✖';
                setTimeout(function () { _this.cbHdmiMsg = ''; }, 3000);
            };
            xhr.send(JSON.stringify({ path: this.filePath }));
        } catch (e) { this.cbHdmiMsg = '✖'; }
    };
'''


def patch_file(path):
    """Patch one bundle; returns 'patched', 'already', or None when it has no stock button."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        return 'already'
    if text.count(TEMPLATE_ANCHOR) != 1 or text.count(METHOD_ANCHOR) != 1:
        return None
    text = text.replace(TEMPLATE_ANCHOR, TEMPLATE_ANCHOR + TEMPLATE_ADD)
    text = text.replace(METHOD_ANCHOR, METHODS + METHOD_ANCHOR)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    st = os.stat(path)
    os.chmod(tmp, st.st_mode & 0o7777)
    try:
        os.chown(tmp, st.st_uid, st.st_gid)
    except OSError:
        pass
    os.replace(tmp, path)
    return 'patched'


def main():
    """Patch every bundle in the build folder that has the download button."""
    build = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUILD
    done = 0
    for path in sorted(glob.glob(os.path.join(build, '*.js'))):
        with open(path, encoding='utf-8') as f:
            if 'DownloadButtonComponent' not in f.read():
                continue
        r = patch_file(path)
        if r:
            print(path + ': ' + r)
            done += 1
        else:
            print(path + ': has DownloadButtonComponent but not the expected text, unchanged')
    if not done:
        print('no bundle with the stock download button found')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
