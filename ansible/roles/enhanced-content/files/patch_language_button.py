#!/usr/bin/env python3
"""
Patch the compiled mediainterface home page (build/6.js) so the language
button shows the name of the active language, e.g. "فارسی ⚙" or "English ⚙",
instead of the word "Language".

The stock template renders {{ 'LANGUAGE_BUTTON' | translate }} next to a gear
icon.  Users could not tell which language was active, and on a box with no
translation for the active language the button read "Language" in English.
HomePage.currentLanguage is the selected entry from languages.json, whose
"text" field is the language's own name.  Until it is set (first render), the
translated word is shown as before.

Idempotent: re-running on an already patched file changes nothing.  Exits
non-zero if the expected template text is not found (e.g. a new mediainterface
release changed it), so Ansible reports it instead of silently doing nothing.

Usage: patch_language_button.py [path/to/6.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/6.js'

# Inside 6.js the Angular template is a JavaScript string literal, so the
# template's single quotes appear escaped as \' in the file.
OLD = "{{ \\'LANGUAGE_BUTTON\\' | translate }} <ion-icon name=\"cog\">"
NEW = ("{{ (currentLanguage && currentLanguage.text) || (\\'LANGUAGE_BUTTON\\' | translate) }}"
       " <ion-icon name=\"cog\">")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8') as f:
        code = f.read()

    if NEW in code:
        print("language button already patched")
        return 0
    if OLD not in code:
        print("language button template not found in " + path + " - not patched")
        return 1

    with open(path, 'w', encoding='utf-8') as f:
        f.write(code.replace(OLD, NEW, 1))
    print("language button patched")
    return 0


if __name__ == '__main__':
    sys.exit(main())
