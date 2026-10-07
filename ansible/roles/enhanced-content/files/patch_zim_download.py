#!/usr/bin/env python3
"""
Hide the zip download button on the media detail page (build/3.js) for cards
that have no zip: ZIM files and Word documents shown as web pages.

ZIM files (offline websites) and .docx files converted to web pages (see
mmiLoader.py) are html cards, and the detail page offers html cards as a
download of html/<slug>.zip.  Neither has a zip (a .zim is also far too big to
download to a phone; a converted Word page links to its original .docx itself),
so the button is hidden for cards whose mimeType is application/x-zim or the
Word .docx type.  Opening the card is unaffected.

Upgrades a 3.js patched by the earlier ZIM-only version of this script.
Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_zim_download.py [path/to/3.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/3.js'

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

# Inside 3.js the Angular template is a JavaScript string literal, so quotes
# inside the template appear escaped as \' in the file.
NO_ZIP = ('{0}?.mimeType !== \\\'application/x-zim\\\' && '
          '{0}?.mimeType !== \\\'' + DOCX + '\\\'')
EDITS = [
    ('<download-button [filePath]="media?.downloadPath"',
     '<download-button *ngIf="' + NO_ZIP.format('media') + '" [filePath]="media?.downloadPath"'),
    ('<download-button [filePath]="episode?.downloadPath"',
     '<download-button *ngIf="' + NO_ZIP.format('episode') + '" [filePath]="episode?.downloadPath"'),
]

# What the earlier ZIM-only version of this script wrote; undone before
# applying EDITS so boxes patched by it are upgraded in place.
ZIM_ONLY = [
    '<download-button *ngIf="media?.mimeType !== \\\'application/x-zim\\\'" [filePath]="media?.downloadPath"',
    '<download-button *ngIf="episode?.mimeType !== \\\'application/x-zim\\\'" [filePath]="episode?.downloadPath"',
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if all(new in code for _, new in EDITS):
        print('ZIM/Word download buttons already hidden')
        return 0
    for (old, _), zim_only in zip(EDITS, ZIM_ONLY):
        code = code.replace(zim_only, old)
    for old, new in EDITS:
        if new not in code and code.count(old) != 1:
            print('detail page download button not found in ' + path + ' - not patched')
            return 1
    for old, new in EDITS:
        if new not in code:
            code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print('ZIM/Word download buttons hidden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
