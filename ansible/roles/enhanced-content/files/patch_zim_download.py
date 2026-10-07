#!/usr/bin/env python3
"""
Detail page buttons (build/3.js) for ZIM files, Word documents and spreadsheets.

ZIM files (offline websites) and .docx/.xlsx/.xls files converted to web pages
(see mmiLoader.py) are html cards.  The stock detail page offers html cards as a
download of html/<slug>.zip and shows the "exit" (open web page) icon on the
open button.  Neither kind has a zip:

  - ZIM (mimeType application/x-zim): the download button is hidden (a .zim
    is also far too big to download to a phone).
  - Word and spreadsheets (their own mimeTypes, WEB_DOCUMENTS): the download
    button downloads the original file from media/<fileName> instead, and the
    open button shows the open book icon used for PDF and EPUB, so a folder of
    Word files looks like a folder of PDFs.  The open button shows the page in
    the same tab (the stock
    code opens web content in a new window after the view report, which old
    phone browsers block as a popup); the page's home button leads back.

Opening the card is unaffected.  Applies to the single-item buttons and to
each episode of a collection.

Upgrades a 3.js patched by the earlier versions of this script (ZIM hidden,
ZIM + Word hidden, Word only).  Idempotent.  Exits non-zero if the expected stock
text is not found.

Usage: patch_zim_download.py [path/to/3.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/3.js'

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
XLS = 'application/vnd.ms-excel'

# Files mmiLoader shows as web pages that keep their own mimeType
WEB_DOCUMENTS = [DOCX, XLSX, XLS]

# Inside 3.js the Angular template is a JavaScript string literal, so quotes
# inside the template appear escaped as \' in the file.
Q = "\\'"


def is_web_document(item, mimes):
    """Template condition: the item is one of the given document types."""
    if len(mimes) == 1:
        return item + '?.mimeType === ' + Q + mimes[0] + Q
    return '(' + ' || '.join(item + '?.mimeType === ' + Q + m + Q for m in mimes) + ')'


def download_edit(item, mimes):
    """(stock, patched) download button opening tag text for media/episode.

    For documents the path swaps html/<slug>.zip in the stock downloadPath for
    media/<fileName>, keeping the language folder the getter already built."""
    stock = '<download-button [filePath]="' + item + '?.downloadPath"'
    original_path = (item + '?.downloadPath.replace(' + Q + 'html/' + Q + ' + ' + item + '?.slug + ' + Q + '.zip' + Q
                     + ', ' + Q + 'media/' + Q + ' + ' + item + '?.fileName)')
    new = ('<download-button *ngIf="' + item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + '"'
           ' [filePath]="' + is_web_document(item, mimes) + ' ? ' + original_path + ' : ' + item + '?.downloadPath"')
    return stock, new


def icon_edit(item, mimes):
    """(stock, patched) open button icon: open book for documents."""
    stock = '<ion-icon [name]="playIcon(' + item + '?.mediaType)"'
    new = '<ion-icon [name]="' + is_web_document(item, mimes) + ' ? ' + Q + 'book' + Q + ' : playIcon(' + item + '?.mediaType)"'
    return stock, new


def open_edit(mimes):
    """(stock, patched) open button: document pages in the same tab, other web
    content in a new window as before."""
    if len(mimes) == 1:
        test = 'resource.mimeType === ' + "'" + mimes[0] + "'"
    else:
        test = '[' + ', '.join("'" + m + "'" for m in mimes) + '].indexOf(resource.mimeType) !== -1'
    return ('subscribe(function () { return window.open(resource.filePath); });',
            'subscribe(function () { if (' + test
            + ') { window.location.href = resource.filePath; } else { window.open(resource.filePath); } });')


def build_edits(mimes):
    """All (stock, patched) pairs for the given document types."""
    return [download_edit('media', mimes), download_edit('episode', mimes),
            icon_edit('media', mimes), icon_edit('episode', mimes), open_edit(mimes)]


EDITS = build_edits(WEB_DOCUMENTS)

# Text written by earlier versions of this script; turned back into the stock
# text before EDITS are applied, so patched boxes are upgraded.
OLD_VERSIONS = [(new, stock) for stock, new in build_edits([DOCX])]  # Word only
for _item in ('media', 'episode'):
    _stock = '<download-button [filePath]="' + _item + '?.downloadPath"'
    # ZIM + Word download hidden
    OLD_VERSIONS.append((
        '<download-button *ngIf="' + _item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + ' && '
        + _item + '?.mimeType !== ' + Q + DOCX + Q + '" [filePath]="' + _item + '?.downloadPath"', _stock))
    # ZIM download hidden
    OLD_VERSIONS.append((
        '<download-button *ngIf="' + _item + '?.mimeType !== ' + Q + 'application/x-zim' + Q + '"'
        ' [filePath]="' + _item + '?.downloadPath"', _stock))


def main():
    """Patch 3.js in place; return 0 when patched or already patched."""
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if all(new in code for _, new in EDITS):
        print('ZIM/Word/spreadsheet detail page buttons already patched')
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
    print('ZIM/Word/spreadsheet detail page buttons patched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
