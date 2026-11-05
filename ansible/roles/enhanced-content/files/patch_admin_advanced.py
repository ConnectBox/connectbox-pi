#!/usr/bin/env python3
"""
Configuration page: "Enable Advanced Options" is remembered in the browser
(connectbox-admin-ui release bundle admin.bundle.js), 2026-11-05.

The button used to show the Advanced options only until the page was
reloaded, and every login reloads it, so Advanced was off again after each
login.  Now the choice is kept in the browser's localStorage: Advanced stays
on after the next login, and pressing the button again hides the options.
(The release's own click handler still runs first and shows them; the added
one then hides them again when Advanced was on.)

The same behaviour is in connectbox-admin-ui source (scripts.js
attachAdvanced); a release built from that source already has it and is left
unchanged.

Idempotent.  Exits non-zero if neither the expected stock text nor the
built-in version is found.

Usage: patch_admin_advanced.py [admin dist directory]
"""
import os
import sys

DEFAULT_DIR = '/var/www/enhanced/admin/dist'
MARKER = 'ConnectBox: Advanced options remembered'
ANCHOR = "  attachAdvanced('advanced', token);"
BUILT_IN = 'connectbox-admin-advanced'
ADD = '''
  // ''' + MARKER + ''' in this browser; pressing the button again hides them
  (function () {
    var KEY = 'connectbox-admin-advanced';
    var remembered = function () { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; } };
    var show = function (on) {
      var els = document.getElementsByClassName('isAdvanced');
      for (var i = 0; i < els.length; i++) {
        if (on) els[i].classList.remove('hidden'); else els[i].classList.add('hidden');
      }
    };
    var button = document.getElementById('advanced-button');
    if (!button) return;
    if (remembered()) show(true);
    button.addEventListener('click', function () {
      var on = !remembered();
      try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {}
      if (!on) { show(false); openSnackBar('Advanced options hidden', 'success'); }
    });
  })();'''


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    path = os.path.join(d, 'admin.bundle.js')
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if MARKER in text:
        print(path + ': already patched')
        return 0
    if BUILT_IN in text:
        print(path + ': built into this release, unchanged')
        return 0
    if text.count(ANCHOR) != 1:
        print(path + ': expected text not found, unchanged')
        return 1
    text = text.replace(ANCHOR, ANCHOR + ADD)
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
