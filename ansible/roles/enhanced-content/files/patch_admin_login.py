#!/usr/bin/env python3
"""
Admin (Configuration) login behaviour (connectbox-admin-ui release bundles).

1. Exit (the logout button) goes to the main ConnectBox screen ("/") instead
   of the login page, and only after the box has ended the session (or 3 s),
   so the logout request is not cancelled by leaving the page.
2. Configuration always asks for the password: the admin page only opens when
   it is reached from another /admin page (the login page, or a reload);
   from the main screen, a bookmark or an old footer link it goes to the
   login page instead.
3. Opening the login page ends any earlier admin session, so an old login
   cookie cannot skip it.  Login waits until that has finished.
4. Leaving the admin page (Exit, back, another link, closing the tab, reload)
   ends the session at once, and coming back to it by Reload, Back or Forward
   goes to the login page (sendBeacon to /admin/api/logout; synchronous
   request on browsers without sendBeacon).  While the page is open and on
   screen it calls /admin/api/keepalive once a minute; connectbox-manage
   ends a session after 5 minutes without an admin request.  If the
   keepalive is refused (401) the page goes to the login page.

5. The login page no longer says what the default password is.

The session expired redirects (HTTP 401 -> login page) are unchanged.

Since 2026-10 the connectbox-admin-ui release is built from source that does
all of this itself; each step then finds its BUILT_IN text and changes nothing.
(Before, the leave step was added a second time on top of the built-in one.)

Idempotent.  Exits non-zero if neither the expected stock text nor the
built-in version is found.

Usage: patch_admin_login.py [admin dist directory]
"""
import os
import sys

DEFAULT_DIR = '/var/www/enhanced/admin/dist'
MARKER = 'ConnectBox: admin login behaviour'
LEAVE_MARKER = 'ConnectBox: admin session ends when the page is left'

ADMIN_EDITS = [
    (
        '  api_get("".concat(api_API_URL, "logout"));\n'
        '  window.location = "/admin/login.html";\n'
        '}\n',

        '  // ' + MARKER + ': end the session on the box, then show the main screen\n'
        '  var cbGone = false;\n'
        '  var cbHome = function cbHome() {\n'
        '    if (!cbGone) { cbGone = true; window.location = "/"; }\n'
        '  };\n'
        '  api_get("".concat(api_API_URL, "logout"), \'\', cbHome, cbHome);\n'
        '  setTimeout(cbHome, 3000);\n'
        '}\n',
    ),
    (
        "var storedToken = localStorage.getItem('admin-authorization');\n",

        '// ' + MARKER + ': always ask for the password when Configuration is\n'
        '// opened; only pages under /admin (login page, reload) lead straight here.\n'
        "var cbFrom = document.referrer || '';\n"
        "var cbSite = window.location.protocol + '//' + window.location.host + '/admin';\n"
        'if (cbFrom.indexOf(cbSite) !== 0) {\n'
        "  window.location.replace('/admin/login.html');\n"
        '  return;\n'
        '}\n'
        "var storedToken = localStorage.getItem('admin-authorization');\n",
    ),
]

LEAVE_EDITS = [
    (
        "window.addEventListener('load', function () {\n"
        "  load(token);\n",

        '// ' + LEAVE_MARKER + ', and is kept alive\n'
        '// (once a minute) only while it is open and on screen.  Reload, Back and\n'
        '// Forward count as having left it, so they go to the login page.\n'
        "var cbNav = '';\n"
        'try {\n'
        "  var cbEntry = performance.getEntriesByType && performance.getEntriesByType('navigation')[0];\n"
        "  if (cbEntry) cbNav = cbEntry.type;\n"
        "  else if (performance.navigation) cbNav = ['navigate', 'reload', 'back_forward'][performance.navigation.type] || '';\n"
        '} catch (e) {}\n'
        "if (cbNav === 'reload' || cbNav === 'back_forward') {\n"
        "  window.location.replace('/admin/login.html');\n"
        '  return;\n'
        '}\n'
        "window.addEventListener('pageshow', function (e) {\n"
        "  if (e.persisted) window.location.replace('/admin/login.html');\n"
        '});\n'
        'var cbEnded = false;\n'
        'var cbEndSession = function cbEndSession() {\n'
        '  if (cbEnded) return;\n'
        '  cbEnded = true;\n'
        '  try {\n'
        '    if (navigator.sendBeacon && navigator.sendBeacon(api_API_URL + "logout")) return;\n'
        '  } catch (e) {}\n'
        '  try {\n'
        '    var x = new XMLHttpRequest();\n'
        '    x.open("get", api_API_URL + "logout", false);\n'
        '    x.send();\n'
        '  } catch (e) {}\n'
        '};\n'
        "if ('onpagehide' in window) window.addEventListener('pagehide', cbEndSession);\n"
        "else window.addEventListener('unload', cbEndSession);\n"
        'setInterval(function () {\n'
        '  if (document.hidden) return;\n'
        '  api_get(api_API_URL + "keepalive", \'\', function () {}, function (code) {\n'
        '    if (code === 401) window.location.href = "/admin/login.html";\n'
        '  });\n'
        '}, 60000);\n'
        "window.addEventListener('load', function () {\n"
        "  load(token);\n",
    ),
]

# Text that shows the release already does a step itself (built from source).
BUILT_IN_ADMIN = ['window.location = "/"', 'document.referrer']
BUILT_IN_LEAVE = ['sendBeacon(', '"keepalive")', "'back_forward'"]
BUILT_IN_LOGIN = ['concat(API_URL, "logout")']

LOGIN_EDITS = [
    (
        "document.getElementById('loginForm').addEventListener('submit', login);\n",

        '// ' + MARKER + ': opening the login page ends any earlier admin session,\n'
        '// so Configuration always asks for the password.  Login waits for it.\n'
        'var cbReady = false;\n'
        'var cbSetReady = function cbSetReady() { cbReady = true; };\n'
        'get("".concat(API_URL, "logout"), \'\', cbSetReady, cbSetReady);\n'
        'setTimeout(cbSetReady, 3000);\n'
        'function cbLogin(e) {\n'
        '  e.preventDefault();\n'
        '  if (cbReady) { login(e); return; }\n'
        '  setTimeout(function () { cbLogin(e); }, 200);\n'
        '}\n'
        "document.getElementById('loginForm').addEventListener('submit', cbLogin);\n",
    ),
]


def patch(path, edits, marker=MARKER, what='login', built_in=()):
    name = os.path.basename(path)
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if marker in code:
        print(name + ': ' + what + ' already patched')
        return 0
    if built_in and all(t in code for t in built_in):
        print(name + ': ' + what + ' built into this release - not patched')
        return 0
    for old, _ in edits:
        if code.count(old) != 1:
            print(name + ': ' + what + ' stock text not found - not patched')
            return 1
    for old, new in edits:
        code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print(name + ': ' + what + ' patched')
    return 0


DEFAULT_PW_TEXT = " Default password is 'connectbox'"


def remove_default_password_text(path):
    name = os.path.basename(path)
    with open(path, encoding='utf-8', newline='') as f:
        html = f.read()
    n = html.count(DEFAULT_PW_TEXT)
    if n == 0:
        print(name + ': default password text already removed')
        return 0
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(html.replace(DEFAULT_PW_TEXT, ''))
    print(name + ': default password text removed')
    return 0


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    rc = patch(os.path.join(d, 'admin.bundle.js'), ADMIN_EDITS, built_in=BUILT_IN_ADMIN)
    rc |= patch(os.path.join(d, 'admin.bundle.js'), LEAVE_EDITS, LEAVE_MARKER, 'leave', BUILT_IN_LEAVE)
    rc |= patch(os.path.join(d, 'login.bundle.js'), LOGIN_EDITS, built_in=BUILT_IN_LOGIN)
    rc |= remove_default_password_text(os.path.join(d, 'login.html'))
    return rc


if __name__ == '__main__':
    sys.exit(main())
