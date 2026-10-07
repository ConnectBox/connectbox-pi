#!/usr/bin/env python3
"""
Detail page buttons (build/3.js) for ZIM files and Word documents.

ZIM files (offline websites) and .docx files converted to web pages (see
mmiLoader.py) are html cards.  The stock detail page offers html cards as a
download of html/<slug>.zip and shows the "exit" (open web page) icon on the
open button.  Neither kind has a zip:

  - ZIM (mimeType application/x-zim): the download button is hidden (a .zim
    is also far too big to download to a phone).
  - Word (.docx mimeType): the download button downloads the original .docx
    from media/<fileName> instead, and the open button shows the open book
    icon used for PDF and EPUB, so a folder of Word files looks like a folder
    of PDFs.

Opening the card is unaffected.  Applies to the single-item buttons and to
each episode of a collection.

Upgrades a 3.js patched by the earlier versions of this script (ZIM only, and
ZIM + Word both hidden).  Idempotent.  Exits non-zero if the expected stock
text is not found.

Usage: patch_zim_download.py [path/to/3.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/3.js'

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

# Inside 3.js the Angular template is a JavaScript string literal, so quotes
# inside the template appear escaped as \' in the file.
Q = "\\'"


def is_docx(item):
    """Template condition: the item is a Word document."""
    return item + '?.mimeType === ' + Q + DOCX + Q


def download_edit(item):
    """(stock, patched) download button opening tag text for media/episode.

    The Word path swaps html/<slug>.zip in the stock downloadPath for
    media/<fileName>, keeping the language folder the getter already built."""
    stock = '<download-button [filePath]="' + item + '?.downloadPath"'
    word_path = (item + '?.downloadPath.replace(' + Q + 'html/' + Q + ' + ' + item + '?.slug + ' + Q + '.zip' + Q
                 + ', ' + Q + 'media/' + Q + ' + ' + item + '?.fileName)')
    new = ('<download-button *ngIf="' + item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + '"'
           ' [filePath]="' + is_docx(item) + ' ? ' + word_path + ' : ' + item + '?.downloadPath"')
    return stock, new


def icon_edit(item):
    """(stock, patched) open button icon: open book for Word documents."""
    stock = '<ion-icon [name]="playIcon(' + item + '?.mediaType)"'
    new = '<ion-icon [name]="' + is_docx(item) + ' ? ' + Q + 'book' + Q + ' : playIcon(' + item + '?.mediaType)"'
    return stock, new


EDITS = [download_edit('media'), download_edit('episode'), icon_edit('media'), icon_edit('episode')]

# Download button text written by earlier versions of this script; turned back
# into the stock text before EDITS are applied, so patched boxes are upgraded.
OLD_VERSIONS = []
for _item in ('media', 'episode'):
    _stock = '<download-button [filePath]="' + _item + '?.downloadPath"'
    # ZIM + Word hidden
    OLD_VERSIONS.append((
        '<download-button *ngIf="' + _item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + ' && '
        + _item + '?.mimeType !== ' + Q + DOCX + Q + '" [filePath]="' + _item + '?.downloadPath"', _stock))
    # ZIM only hidden
    OLD_VERSIONS.append((
        '<download-button *ngIf="' + _item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + '"'
        ' [filePath]="' + _item + '?.downloadPath"', _stock))


def main():
    """Patch 3.js in place; return 0 when patched or already patched."""
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if all(new in code for _, new in EDITS):
        print('ZIM/Word detail page buttons already patched')
        return 0
    # Undo earlier versions of the patch (each old text occurs at most once)
    for old, stock in OLD_VERSIONS:
        code = code.replace(old, stock)
    # Check every stock text is there exactly once before changing anything
    for old, new in EDITS:
        if new not in code and code.count(old) != 1:
            print('detail page button not found in ' + path + ' - not patched')
            return 1
    for old, new in EDITS:
        if new not in code:
            code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print('ZIM/Word detail page buttons patched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
