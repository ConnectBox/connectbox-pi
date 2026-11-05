#!/usr/bin/env python3
"""
Client Wi-Fi "wipe" button on the Configuration page (connectbox-admin-ui
release bundles), 2026-11-05.

Under "Connect To Wi-Fi Hotspot" (shown when the section is opened) a row
"Wipe client SSID and password (also forgets the remembered networks)" with a
play button.  It asks for confirmation, then calls GET /admin/api/do/clientwifiwipe
(connectbox-manage): the client SSID and password go back to the build
defaults (Default / Default1), PxUSBm's remembered networks are removed, and
the client Wi-Fi is restarted.  The SSID and password fields then show the
defaults.

The same button is in connectbox-admin-ui source (client_wifiwipe.pug,
scripts.js attachClientWifiWipe); a release built from that source already
has it, and each step then finds its built-in text and changes nothing.

Idempotent.  Exits non-zero if neither the expected stock text nor the
built-in version is found.

Usage: patch_admin_clientwifi_wipe.py [admin dist directory]
"""
import os
import sys

DEFAULT_DIR = '/var/www/enhanced/admin/dist'
MARKER = 'ConnectBox: client Wi-Fi wipe button'

PLAY_ICON = ('<svg class="bi" xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
             'fill="currentColor" viewBox="0 0 16 16"><path d="M10.804 8 5 4.633v6.734L10.804 8zm.792-.696'
             'a.802.802 0 0 1 0 1.392l-6.363 3.692C4.713 12.69 4 12.345 4 11.692V4.308c0-.653.713-.998 '
             '1.233-.696l6.363 3.692z"></path></svg>')

HTML_ANCHOR = ('id="client-wifi-restart-input" placeholder="Wifi Restart Hidden Field" '
               'name="wifi-restart" value="client"/></div></div>')
HTML_ADD = ('<!-- ' + MARKER + ' --><div class="form-accordion-content hidden mb-4 ms-15-icon me-5">'
            '<div class="d-flex align-items-center"><span class="flex-grow-1">'
            'Wipe client SSID and password (also forgets the remembered networks)</span>'
            '<button class="bg-transparent border-0 text-primary p-0" id="clientwifiwipe-button" '
            'type="button">' + PLAY_ICON + '</button></div></div>')
HTML_BUILT_IN = 'id="clientwifiwipe-button"'

JS_ANCHOR = "  attachAdvanced('advanced', token);"
JS_ADD = '''
  // ''' + MARKER + ''': ask, then GET do/clientwifiwipe
  (function () {
    var button = document.getElementById('clientwifiwipe-button');
    if (!button) return;
    button.addEventListener('click', function () {
      if (!window.confirm('Wipe the client Wi-Fi SSID and password, and forget all remembered networks? The box will disconnect from the internet Wi-Fi.')) return;
      openSnackBar('Processing...', 'success');
      api_get("".concat(api_API_URL, "do/clientwifiwipe"), token, function () {
        var ssid = document.getElementById('client-ssid-input');
        var pass = document.getElementById('client-wifipassword-input');
        if (ssid) ssid.value = 'Default';
        if (pass) pass.value = 'Default1';
        openPopup('Success', 'Client Wi-Fi wiped');
      }, function (code) {
        if (code === 401) window.location.href = "/admin/login.html";
        openSnackBar('Wipe client Wi-Fi failed', 'error');
      });
    });
  })();'''
JS_BUILT_IN = 'do/clientwifiwipe'


def patch(path, anchor, add, built_in):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        print(path + ': already patched')
        return True
    if built_in in text:
        print(path + ': built into this release, unchanged')
        return True
    if text.count(anchor) != 1:
        print(path + ': expected text not found (' + str(text.count(anchor)) + ' matches), unchanged')
        return False
    text = text.replace(anchor, anchor + add)
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
    print(path + ': patched')
    return True


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    ok = patch(os.path.join(d, 'index.html'), HTML_ANCHOR, HTML_ADD, HTML_BUILT_IN)
    ok = patch(os.path.join(d, 'admin.bundle.js'), JS_ANCHOR, JS_ADD, JS_BUILT_IN) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
