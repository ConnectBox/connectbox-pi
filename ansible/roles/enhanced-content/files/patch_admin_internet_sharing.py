#!/usr/bin/env python3
"""
"Share Internet With Wi-Fi Users" switch on the Configuration page
(connectbox-admin-ui release bundles), 2026-11-05.

An Advanced option (shown after "Advanced") under "Connect To Wi-Fi Hotspot":
a switch for brand.j2 "internet_sharing" (PxUSBm then turns NAT forwarding
and real DNS on or off), with a warning about metered uplinks, and the data
passed so far (connectbox-manage internetusage) with a "Reset data counter"
button (do/internetusagereset).  It is built
from the release's own "Don't Mount USB" switch (same markup and behaviour),
with the ids, title and icon changed.

The same switch is in connectbox-admin-ui source (internet_sharing.pug in
client_wi_fi.pug, load.js, update.js, scripts.js attachInternetUsage); a release built from that source
already has it, and each step then finds its built-in text and changes
nothing.

Idempotent.  Exits non-zero if neither the expected stock text nor the
built-in version is found.

Usage: patch_admin_internet_sharing.py [admin dist directory]
"""
import os
import sys

DEFAULT_DIR = '/var/www/enhanced/admin/dist'
MARKER = 'ConnectBox: internet sharing switch'
WARN = ("Lets phones on the ConnectBox Wi-Fi use this box's internet connection (Ethernet or the client "
        "Wi-Fi above). Warning: if that connection is metered (mobile data, pay per MB), every phone's "
        "traffic, including app and system updates, counts against it. No filtering. Turning this on or off "
        "disconnects the phones once (they rejoin). Phones will not open the ConnectBox page by themselves "
        "while this is on: use http://connectbox")
USAGE_HTML = ('<p class="mb-1" id="internet_usage-text">Data shared: -</p><div class="mb-3">'
              '<button class="bg-transparent border-0 text-primary p-0" id="internetusagereset-button" '
              'type="button">Reset data counter</button></div>')
TITLE = 'Share Internet With Wi-Fi Users'

HTML_ANCHOR = 'id="client_wifi-loader"></div></div></div></div></form>'
HTML_BUILT_IN = 'id="internet_sharing-switch"'
JS_EDITS = [
    ("  getProperty('usb0nomount', 'brand/usb0nomount', token, switchRenderer);",
     "\n  getProperty('internet_sharing', 'brand/internet_sharing', token, switchRenderer); // " + MARKER),
    ("  attachUpdateBrandCallbackToSwitch('usb0nomount', 'usb0nomount', token);",
     "\n  attachUpdateBrandCallbackToSwitch('internet_sharing', 'internet_sharing', token); // " + MARKER),
    # data total and its Reset button (in the system buttons' module, which has
    # api_get, api_API_URL and openSnackBar)
    ("  attachAdvanced('advanced', token);", """
  // """ + MARKER + """: data total (GET internetusage) and Reset (do/internetusagereset)
  (function () {
    var text = document.getElementById('internet_usage-text');
    var button = document.getElementById('internetusagereset-button');
    if (!text) return;
    var fmt = function (b) {
      b = Number(b) || 0;
      if (b >= 1e9) return (b / 1e9).toFixed(2) + ' GB';
      if (b >= 1e6) return (b / 1e6).toFixed(1) + ' MB';
      if (b >= 1e3) return (b / 1e3).toFixed(1) + ' kB';
      return b + ' bytes';
    };
    var show = function () {
      api_get("".concat(api_API_URL, "internetusage"), token, function (result) {
        var u = result && result[0] || {};
        var up = Number(u.up) || 0, down = Number(u.down) || 0;
        text.textContent = 'Data shared: ' + fmt(up + down) + ' (down ' + fmt(down) + ', up ' + fmt(up) + ')' +
          (u.since ? ' since ' + u.since : '');
      }, function () {});
    };
    show();
    if (button) button.addEventListener('click', function () {
      if (!window.confirm('Set the shared data counter back to 0?')) return;
      api_get("".concat(api_API_URL, "do/internetusagereset"), token, function () {
        show();
        openSnackBar('Data counter reset', 'success');
      }, function (code) {
        if (code === 401) window.location.href = "/admin/login.html";
        openSnackBar('Reset data counter failed', 'error');
      });
    });
  })();"""),
]
JS_BUILT_IN = "'brand/internet_sharing'"


def region_html(text):
    """The internet sharing switch, made from the release's "Don't Mount USB" one."""
    a = text.index('<div class="allUsers hidden isAdvanced" id="usbnomountregion">')
    b = text.index('</form></div>', a) + len('</form></div>')
    r = text[a:b]
    # icon: the globe of "Client Wifi Country Code"
    i = text.index('<label for="client-wificountry-input">')
    globe = text[text.rindex('<svg', 0, i):i]
    s0 = r.index('<svg')
    s1 = r.index('</svg>', s0) + len('</svg>')
    r = r[:s0] + globe + r[s1:]
    r = r.replace('usbnomountregion', 'internetsharingregion').replace('usb0nomount', 'internet_sharing')
    r = r.replace('Don’t Mount USB', TITLE, 1).replace('Don’t Mount USB', 'Share Internet')
    content = 'id="internet_sharing">'
    k = r.index(content) + len(content)
    r = r[:k] + '<p class="text-caption">' + WARN + '</p>' + USAGE_HTML + r[k:]
    return '<!-- ' + MARKER + ' -->' + r


def write_like(path, text):
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


def patch_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        print(path + ': already patched')
        return True
    if HTML_BUILT_IN in text:
        print(path + ': built into this release, unchanged')
        return True
    try:
        if text.count(HTML_ANCHOR) != 1:
            raise ValueError(str(text.count(HTML_ANCHOR)) + ' insertion points')
        add = region_html(text)
    except ValueError as e:
        print(path + ': expected text not found (' + str(e) + '), unchanged')
        return False
    write_like(path, text.replace(HTML_ANCHOR, HTML_ANCHOR + add))
    print(path + ': patched')
    return True


def patch_js(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        print(path + ': already patched')
        return True
    if JS_BUILT_IN in text:
        print(path + ': built into this release, unchanged')
        return True
    for anchor, _ in JS_EDITS:
        if text.count(anchor) != 1:
            print(path + ': expected text not found (' + anchor.strip() + '), unchanged')
            return False
    for anchor, add in JS_EDITS:
        text = text.replace(anchor, anchor + add)
    write_like(path, text)
    print(path + ': patched')
    return True


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    ok = patch_html(os.path.join(d, 'index.html'))
    ok = patch_js(os.path.join(d, 'admin.bundle.js')) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
