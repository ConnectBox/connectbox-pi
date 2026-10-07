#!/usr/bin/env python3
"""
Show the file size next to every download button (build/*.js).

Users want to know how big a download is before they start it (videos can be
hundreds of MB).  The download button component (DownloadButtonComponent) is
compiled into several bundles - the media detail page and each viewer - so
every bundle that contains it is patched:

  - a method cbSizeText() asks the box for the file's size with a HEAD request
    (headers only, instant on the local WiFi) the first time it sees a file
    path, and returns the size as text ("3.4 KB", "412 MB", "1.2 GB") once
    the answer arrives;
  - the button's template shows that text in a small label before the icon.

Nothing is shown when the size is unknown: the request failed, the server sent
no Content-Length, or the reply is the app's start page (nginx answers a
missing file with index.html, so a text/html reply for a non-.html path is
ignored).  Units are the same in every language, so no translation is needed.
Plain ES5 + XMLHttpRequest so it runs on iOS 9 / Android 4 browsers; Angular's
zone.js notices the XHR callback and redraws the label.

Idempotent.  Exits non-zero if no bundle contains the stock button.

Usage: patch_download_size.py [path/to/build]
"""
import glob
import os
import sys

DEFAULT_BUILD = '/var/www/enhanced/content/www/build'

MARKER = 'DownloadButtonComponent.prototype.cbSizeText'

# Inside the bundles the Angular template is a JavaScript string literal, so
# quotes inside the template appear escaped as \' in the file.
TEMPLATE_OLD = ('\'<ion-spinner [hidden]="!isDownloading" [ngClass]="inNavBar ? \\\'spinner-light\\\' : \\\'\\\'"></ion-spinner>\\n'
                '<button ion-button clear icon-only')
TEMPLATE_NEW = ('\'<ion-spinner [hidden]="!isDownloading" [ngClass]="inNavBar ? \\\'spinner-light\\\' : \\\'\\\'"></ion-spinner>\\n'
                '<span class="cb-size" [hidden]="!cbSizeText()" [style.color]="inNavBar ? \\\'#fff\\\' : \\\'\\\'"'
                ' style="font-size:13px;vertical-align:middle;white-space:nowrap;">{{ cbSize }}</span>\\n'
                '<button ion-button clear icon-only')

METHOD_ANCHOR = '    DownloadButtonComponent.prototype.downloadFile = function () {'
METHOD = '''    /**
     * ConnectBox: the size of the file as text ("" until known), from a HEAD
     * request made the first time a file path is seen.
     */
    DownloadButtonComponent.prototype.cbSizeText = function () {
        var _this = this;
        var path = this.filePath;
        if (!path) { return ''; }
        if (this.cbSizePath !== path) {
            this.cbSizePath = path;
            this.cbSize = '';
            try {
                var xhr = new XMLHttpRequest();
                xhr.open('HEAD', path, true);
                xhr.onreadystatechange = function () {
                    if ((xhr.readyState !== 4) || (_this.cbSizePath !== path)) { return; }
                    var type = xhr.getResponseHeader('Content-Type') || '';
                    var n = parseInt(xhr.getResponseHeader('Content-Length'), 10);
                    if ((xhr.status !== 200) || isNaN(n) || (n < 0)) { return; }
                    if ((type.indexOf('text/html') === 0) && !/\\.html?$/i.test(path)) { return; }
                    var units = ['B', 'KB', 'MB', 'GB', 'TB'];
                    var i = 0;
                    while ((n >= 1024) && (i < units.length - 1)) { n = n / 1024; i++; }
                    _this.cbSize = ((i > 0) && (n < 10) ? n.toFixed(1) : Math.round(n)) + ' ' + units[i];
                };
                xhr.send();
            } catch (e) { }
        }
        return this.cbSize;
    };
'''


def patch_file(path):
    """Patch one bundle.  Returns 'patched', 'already' or 'absent'."""
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if 'DownloadButtonComponent' not in code or TEMPLATE_OLD not in code and MARKER not in code:
        return 'absent'
    if MARKER in code and TEMPLATE_NEW in code:
        return 'already'
    if code.count(TEMPLATE_OLD) != 1 or code.count(METHOD_ANCHOR) != 1:
        return 'absent'
    code = code.replace(TEMPLATE_OLD, TEMPLATE_NEW, 1)
    code = code.replace(METHOD_ANCHOR, METHOD + METHOD_ANCHOR, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    return 'patched'


def main():
    """Patch every bundle in the build folder that contains the button."""
    build = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUILD
    results = {}
    for path in sorted(glob.glob(os.path.join(build, '*.js'))):
        result = patch_file(path)
        if result != 'absent':
            results[os.path.basename(path)] = result
    if not results:
        print('download button not found in ' + build + ' - not patched')
        return 1
    print('download sizes: ' + ', '.join(name + ' ' + r for name, r in sorted(results.items())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
