#!/usr/bin/env python3
"""
Use the box's current language settings for returning visitors (build/main.js).

The app remembers the visitor's language in browser storage.  On the next visit
LanguageProvider.getLanguage() looks the saved language up in languages.json,
but then rebuilds it from the *saved* copy - so anything the box changed since
(most importantly "rtl": true, which flips the page to right-to-left for
Farsi/Arabic) never reached anyone who had visited before.  Found on the test
unit: a returning browser kept isRtl false and the Farsi page stayed
left-to-right.

This patch rebuilds the language from the matching languages.json entry
instead; the saved copy is only used to know which language was chosen.

Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_saved_language.py [path/to/main.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/main.js'

OLD = ('var lang = new __WEBPACK_IMPORTED_MODULE_9__models_language__["a" /* Language */]'
       '(parsed_1.codes, parsed_1.text, parsed_1.isDefault, parsed_1.isRtl);')
NEW = ('var lang = new __WEBPACK_IMPORTED_MODULE_9__models_language__["a" /* Language */]'
       '(found.codes, found.text, found.isDefault, found.isRtl); // ConnectBox: current languages.json settings')


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if NEW in code:
        print('saved-language patch already applied')
        return 0
    if code.count(OLD) != 1:
        print('LanguageProvider stock text not found in ' + path + ' - not patched')
        return 1
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code.replace(OLD, NEW, 1))
    print('saved-language patch applied')
    return 0


if __name__ == '__main__':
    sys.exit(main())
