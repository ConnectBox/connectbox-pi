#!/usr/bin/env python3
"""
Translate the footer's "Configuration" (admin) link (build/6.js).

The footer is a single shared HTML file (assets/content/footer.html) that the
AppFooterComponent inserts as-is, so its "Configuration" link was English in
every language.  This patch gives the component the app's TranslateService and
replaces the text of the <a href="/admin"> link with the FOOTER_CONFIGURATION
string from the selected language's interface.json, on load and whenever the
language changes.  If the string is missing the footer is left as it is.

Edits to the stock component:
  - load ngx-translate (webpack module 63, the one HomePage already uses);
  - add TranslateService to the constructor and its design:paramtypes metadata
    (the app is compiled JIT, so Angular injects from that metadata);
  - relabel the admin link after the footer HTML is loaded.

Idempotent.  Exits non-zero if the expected stock text is not found.

Usage: patch_footer_translation.py [path/to/6.js]
"""
import sys

DEFAULT_PATH = '/var/www/enhanced/content/www/build/6.js'
MARKER = 'ConnectBox: footer admin link in the selected language'

EDITS = [
    (
        "var AppFooterComponent = /** @class */ (function () {\n"
        "    function AppFooterComponent(http) {",

        "// " + MARKER + "\n"
        "var __CB_ngx_translate__ = __webpack_require__(63);\n"
        "var AppFooterComponent = /** @class */ (function () {\n"
        "    function AppFooterComponent(http, translate) {",
    ),
    (
        "            _this.content = response;\n",

        "            _this.content = response;\n"
        "            // ConnectBox: show the footer's admin link in the selected language\n"
        "            _this.cbTranslate = function (html) {\n"
        "                var label = translate.instant('FOOTER_CONFIGURATION');\n"
        "                if (!label || label === 'FOOTER_CONFIGURATION') { return html; }\n"
        "                return html.replace(/(<a href=\"\\/admin\">)[^<]*(<\\/a>)/, function (m, open, close) { return open + label + close; });\n"
        "            };\n"
        "            _this.content = _this.cbTranslate(_this.content);\n"
        "            translate.onLangChange.subscribe(function () { _this.content = _this.cbTranslate(_this.content); });\n",
    ),
    (
        "        __metadata(\"design:paramtypes\", [__WEBPACK_IMPORTED_MODULE_2__angular_common_http__[\"a\" /* HttpClient */]])\n"
        "    ], AppFooterComponent);",

        "        __metadata(\"design:paramtypes\", [__WEBPACK_IMPORTED_MODULE_2__angular_common_http__[\"a\" /* HttpClient */],\n"
        "            __CB_ngx_translate__[\"c\" /* TranslateService */]])\n"
        "    ], AppFooterComponent);",
    ),
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    if MARKER in code:
        print('footer translation already patched')
        return 0
    for old, _ in EDITS:
        if code.count(old) != 1:
            print('footer component stock text not found in ' + path + ' - not patched')
            return 1
    for old, new in EDITS:
        code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print('footer translation patched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
