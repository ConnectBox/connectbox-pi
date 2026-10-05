#!/usr/bin/env python3
"""
Hide the download button for ZIM cards on the media detail page (build/3.js).

ZIM files (offline websites, see mmiLoader.py) are web-content cards, and the
detail page offers web content as a download of html/<slug>.zip.  A ZIM has
no zip (and the .zim itself is far too big to download to a phone), so the
button is hidden for cards whose mimeType is application/x-zim.  Opening the
card is unaffected.

Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_zim_download.py [path/to/3.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/3.js'

# Inside 3.js the Angular template is a JavaScript string literal, so quotes
# inside the template appear escaped as \' in the file.
EDITS = [
    ('<download-button [filePath]="media?.downloadPath"',
     '<download-button *ngIf="media?.mimeType !== \\\'application/x-zim\\\'" [filePath]="media?.downloadPath"'),
    ('<download-button [filePath]="episode?.downloadPath"',
     '<download-button *ngIf="episode?.mimeType !== \\\'application/x-zim\\\'" [filePath]="episode?.downloadPath"'),
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if all(new in code for _, new in EDITS):
        print('ZIM download button already hidden')
        return 0
    for old, new in EDITS:
        if new not in code and code.count(old) != 1:
            print('detail page download button not found in ' + path + ' - not patched')
            return 1
    for old, new in EDITS:
        if new not in code:
            code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print('ZIM download button hidden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
