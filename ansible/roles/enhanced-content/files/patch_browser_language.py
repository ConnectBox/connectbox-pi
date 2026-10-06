#!/usr/bin/env python3
"""
Start a first-time visitor in their browser's language, if the box has it
(build/main.js, LanguageProvider.getLanguage).

Stock behaviour since mediainterface 70a4923 (2023-07-19, "Don't consult
browser"): a visitor with no saved language always gets the box's default
language from languages.json.  This patch walks the browser's preferred
languages in order (navigator.languages - the same list the browser sends as
the Accept-Language header; navigator.language / userLanguage on old phones
that lack it) and picks the first one the box has.  For each browser language,
in the browser's order:

  1. exact code match, ignoring case ("pt-br" == "pt-BR"), else
  2. same base language ("pt-BR" -> "pt", "zh-TW" -> "zh-CN").

So "fr-FR, es-MX, en" on a box without French gives Spanish, not English.

If none of them is on the box, the default from languages.json is used as
before.  A language the visitor picked in the language menu is saved by the
app and always wins - this only decides the starting language.  The browser
choice is not saved, so it is re-checked on each visit until the visitor
picks one.  Plain loops instead of Array.find, for old Android browsers.

Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_browser_language.py [path/to/main.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/main.js'

OLD = ("            // 20230719 Don't consult browser.  Use default if needed.\n"
       "            return _this.getDefaultLanguage();\n")
MARKER = "// ConnectBox: browser language if the box has it"
NEW = ("            " + MARKER + ", else the default (patch_browser_language.py)\n"
       "            return _this.supported().pipe(Object(__WEBPACK_IMPORTED_MODULE_7_rxjs_operators_map__[\"map\"])(function (supported) {\n"
       "                var wanted = [];\n"
       "                try {\n"
       "                    wanted = (navigator.languages && navigator.languages.length) ? navigator.languages\n"
       "                        : [navigator.language || navigator.userLanguage || ''];\n"
       "                }\n"
       "                catch (e) { }\n"
       "                var pick = function (w, same) {\n"
       "                    for (var j = 0; j < supported.length; j++) {\n"
       "                        var codes = supported[j].codes || [];\n"
       "                        for (var k = 0; k < codes.length; k++) {\n"
       "                            if (same(w, String(codes[k]).toLowerCase())) { return supported[j]; }\n"
       "                        }\n"
       "                    }\n"
       "                    return null;\n"
       "                };\n"
       "                for (var i = 0; i < wanted.length; i++) {\n"
       "                    var w = String(wanted[i] || '').toLowerCase();\n"
       "                    if (!w) { continue; }\n"
       "                    var found = pick(w, function (a, c) { return a === c; })\n"
       "                        || pick(w, function (a, c) { return a.split('-')[0] === c.split('-')[0]; });\n"
       "                    if (found) { return found; }\n"
       "                }\n"
       "                for (var d = 0; d < supported.length; d++) {\n"
       "                    if (supported[d].isDefault) { return supported[d]; }\n"
       "                }\n"
       "                return supported[0];\n"
       "            }));\n")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if MARKER in code:
        print('browser-language patch already applied')
        return 0
    if code.count(OLD) != 1:
        print('LanguageProvider default-language text not found in ' + path + ' - not patched')
        return 1
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code.replace(OLD, NEW, 1))
    print('browser-language patch applied')
    return 0


if __name__ == '__main__':
    sys.exit(main())
