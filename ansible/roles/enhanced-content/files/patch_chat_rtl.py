#!/usr/bin/env python3
"""
Chat page: translated labels and right-to-left support (build/2.js, build/main.css).

These edits were first made by hand on the NanoPi NEO test unit (2026-10-05) and
are reproduced here exactly, so re-provisioning keeps them:

  2.js (ChatPage)
  - Chat title, "Name" and "Type a message" come from the selected language's
    interface.json (CHAT_TITLE, CHAT_NAME, CHAT_MESSAGE), English by default.
  - Each message carries its text direction (the language's direction, or the
    first strong character of the text), and bubbles are placed by direction
    instead of by sender; your own messages are marked green (cb-mine).
  - Own messages are no longer shown twice in an empty chat.
  main.css
  - Bubble colours for own/other messages, and bubble placement that does not
    depend on the page direction (right-hand bubbles went off-screen on RTL pages).

Idempotent.  Exits non-zero if a stock text fragment is missing (e.g. a new
mediainterface release changed it), so Ansible reports it.

Usage: patch_chat_rtl.py [build_dir]   (default /var/www/enhanced/content/www/build)
"""
import os
import re
import sys

BUILD = sys.argv[1] if len(sys.argv) > 1 else '/var/www/enhanced/content/www/build'

# (stock text, patched text) pairs for 2.js, applied in order
JS_EDITS = [("        this.url = '';\n        this.storage = storage;", "        this.url = '';\n        this.storage = storage;\n        // ConnectBox: chat labels follow the selected language (from <lang>/data/interface.json)\n        this.labels = { CHAT_TITLE: 'Chat', CHAT_NAME: 'Name', CHAT_MESSAGE: 'Type a message' };\n        storage.get('language').then(function (val) {\n            var code = 'en';\n            var rtlFlag = false;\n            try { if (val) { var L = JSON.parse(val); code = L.code || 'en'; rtlFlag = !!L.isRtl; } } catch (e) { }\n            _this.myDir = (rtlFlag || ['ar', 'arc', 'ckb', 'dv', 'fa', 'he', 'iw', 'ps', 'sd', 'ug', 'ur', 'yi'].indexOf(code) !== -1) ? 'rtl' : 'ltr';\n            http.get('assets/content/' + code + '/data/interface.json').subscribe(function (iface) {\n                ['CHAT_TITLE', 'CHAT_NAME', 'CHAT_MESSAGE'].forEach(function (k) { if (iface && iface[k]) { _this.labels[k] = iface[k]; } });\n            }, function () { });\n        });"), ('                // Filter out my own chats from API since page reloaded\n                if (_this.timeStamp > 0) {', '                // Filter out my own chats from API since page reloaded\n                if (_this.timeStamp > 0 || _this.chats.length > 0) { // ConnectBox: also skip my own messages already shown in an empty chat'), ('    ChatPage.prototype.sendMessage = function () {', "    ChatPage.prototype.sendMessage = function () {\n        // ConnectBox: work out this message's own text direction and send it with the message\n        this.data.dir = this.myDir || (function (text) {\n            var rtl = /[\u0590-ࣿיִ-﷿ﹰ-\ufeff]/;\n            var ltr = /[A-Za-zÀ-ɏͰ-ԯऀ-\u0dff\u0e00-\u0fff\u3040-ヿ㐀-鿿가-\ud7af]/;\n            text = text || '';\n            for (var i = 0; i < text.length; i++) {\n                var c = text.charAt(i);\n                if (rtl.test(c)) { return 'rtl'; }\n                if (ltr.test(c)) { return 'ltr'; }\n            }\n            return 'auto';\n        })(this.data.body);"), ('        Object(__WEBPACK_IMPORTED_MODULE_0__angular_core__["m" /* Component */])({\n            selector: \'page-chat\',template:/*ion-inline-start:"/home/runner/work/mediainterface/mediainterface/src/pages/chat/chat.html"*/\'<ion-header>\\n  <ion-navbar hideBackButton>\\n    <ion-buttons left>\\n        <button ion-button icon-only (click)="goHome()">\\n            <ion-icon name="arrow-back"></ion-icon>\\n        </button>\\n    </ion-buttons>\\n    <ion-title right><ion-icon name="chatbubbles"></ion-icon>&nbsp;Chat</ion-title>\\n  </ion-navbar>\\n</ion-header>\\n<ion-content >\\n  <ion-list content>\\n    <ion-item *ngFor="let chat of chats" no-lines>\\n      <div class="chat-status" text-center *ngIf="chat.type===\\\'join\\\'||chat.type===\\\'exit\\\';else message">\\n        <span class="chat-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n        <span class="chat-content-center">{{chat.body}}</span>\\n      </div>\\n      <ng-template #message>\\n        <div class="chat-message" text-right *ngIf="chat.nick === nickname">\\n          <div class="right-bubble">\\n            <span class="msg-name">{{chat.nick}}</span>\\n            <span class="msg-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n            <p text-wrap>{{chat.body}}</p>\\n          </div>\\n        </div>\\n        <div class="chat-message" text-left *ngIf="chat.nick !== nickname">\\n          <div class="left-bubble">\\n            <span class="msg-name">{{chat.nick}}</span>\\n            <span class="msg-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n            <p text-wrap>{{chat.body}}</p>\\n          </div>\\n        </div>\\n      </ng-template>\\n    </ion-item>\\n  </ion-list>\\n</ion-content>\\n<ion-footer>\\n  <form #chatForm (ngSubmit)="sendMessage()">\\n    <ion-grid>\\n      <ion-row>\\n        <ion-col col-2>\\n          <ion-input type="text" placeholder="{{ nickname }}" [(ngModel)]="data.nick" name="nick"></ion-input>\\n        </ion-col>\\n        <ion-col col-9>\\n          <ion-input type="text" placeholder="Type a message" [(ngModel)]="data.body" name="body"></ion-input>\\n        </ion-col>\\n        <ion-col col-1 text-right>\\n          <button ion-button icon-only clear>\\n            <ion-icon name="paper-plane"></ion-icon>\\n          </button>\\n        </ion-col>\\n      </ion-row>\\n    </ion-grid>\\n  </form>\\n</ion-footer>\\n\'/*ion-inline-end:"/home/runner/work/mediainterface/mediainterface/src/pages/chat/chat.html"*/,', '        Object(__WEBPACK_IMPORTED_MODULE_0__angular_core__["m" /* Component */])({\n            selector: \'page-chat\',template:/*ion-inline-start:"/home/runner/work/mediainterface/mediainterface/src/pages/chat/chat.html"*/\'<ion-header>\\n  <ion-navbar hideBackButton>\\n    <ion-buttons left>\\n        <button ion-button icon-only (click)="goHome()">\\n            <ion-icon name="arrow-back"></ion-icon>\\n        </button>\\n    </ion-buttons>\\n    <ion-title right><ion-icon name="chatbubbles"></ion-icon>&nbsp;{{ labels.CHAT_TITLE }}</ion-title>\\n  </ion-navbar>\\n</ion-header>\\n<ion-content >\\n  <ion-list content>\\n    <ion-item *ngFor="let chat of chats" no-lines>\\n      <div class="chat-status" text-center *ngIf="chat.type===\\\'join\\\'||chat.type===\\\'exit\\\';else message">\\n        <span class="chat-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n        <span class="chat-content-center" dir="auto">{{chat.body}}</span>\\n      </div>\\n      <ng-template #message>\\n        <div class="chat-message" text-right dir="rtl" *ngIf="chat.dir === \\\'rtl\\\'">\\n          <div class="right-bubble" [class.cb-mine]="chat.nick === (data.nick || nickname)">\\n            <span class="msg-name">{{chat.nick}}</span>\\n            <span class="msg-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n            <p text-wrap>{{chat.body}}</p>\\n          </div>\\n        </div>\\n        <div class="chat-message" text-left dir="ltr" *ngIf="chat.dir !== \\\'rtl\\\'">\\n          <div class="left-bubble" [class.cb-mine]="chat.nick === (data.nick || nickname)">\\n            <span class="msg-name">{{chat.nick}}</span>\\n            <span class="msg-date">{{chat.timestamp * 1000 | date:\\\'short\\\'}}</span>\\n            <p text-wrap>{{chat.body}}</p>\\n          </div>\\n        </div>\\n      </ng-template>\\n    </ion-item>\\n  </ion-list>\\n</ion-content>\\n<ion-footer>\\n  <form #chatForm (ngSubmit)="sendMessage()">\\n    <ion-grid>\\n      <ion-row>\\n        <ion-col col-2>\\n          <ion-input type="text" placeholder="{{ labels.CHAT_NAME }}: {{ nickname }}" [(ngModel)]="data.nick" name="nick"></ion-input>\\n        </ion-col>\\n        <ion-col col-9>\\n          <ion-input type="text" placeholder="{{ labels.CHAT_MESSAGE }}" [(ngModel)]="data.body" name="body"></ion-input>\\n        </ion-col>\\n        <ion-col col-1 text-right>\\n          <button ion-button icon-only clear>\\n            <ion-icon name="paper-plane"></ion-icon>\\n          </button>\\n        </ion-col>\\n      </ion-row>\\n    </ion-grid>\\n  </form>\\n</ion-footer>\\n\'/*ion-inline-end:"/home/runner/work/mediainterface/mediainterface/src/pages/chat/chat.html"*/,')]

CSS_MARKER = '/* ConnectBox: bubble side follows language direction'
CSS_BLOCK = "/* ConnectBox: bubble side follows language direction; green = your own message */\npage-chat .chat-message .left-bubble.cb-mine { background: #dcf8c6; }\npage-chat .chat-message .left-bubble.cb-mine:after { border-right-color: #dcf8c6; }\npage-chat .chat-message .left-bubble.cb-mine span.msg-name { color: green; }\npage-chat .chat-message .right-bubble:not(.cb-mine) { background: #ffffff; }\npage-chat .chat-message .right-bubble:not(.cb-mine):after { border-left-color: #ffffff; }\npage-chat .chat-message .right-bubble:not(.cb-mine) span.msg-name { color: blue; }\n\n/* ConnectBox: fixed bubble placement that does not depend on the page direction\n   (the original 'left: 15%' pushed right-hand bubbles off-screen on right-to-left pages) */\npage-chat .chat-message .right-bubble { left: 0; margin-left: 15%; margin-right: 30px; }\npage-chat .chat-message .left-bubble { left: 0; margin-left: 30px; margin-right: 15%; }\npage-chat .chat-message .right-bubble p, page-chat .chat-message .left-bubble p { white-space: normal; }\n"


# The compiled template comments carry the folder the release was built in on
# GitHub Actions: /home/runner/work/<repo>/<repo>/.  JS_EDITS were written
# against RT-coding-team's "mediainterface" builds; releases built from
# ConnectBox/connectbox-mediainterface (from 2026-10-06) have a different
# folder, so the edits are adjusted to whatever folder this 2.js was built in.
STOCK_BUILD_ROOT = '/home/runner/work/mediainterface/mediainterface/'


def edits_for(code):
    """JS_EDITS with the build folder replaced by the one used in this 2.js."""
    m = re.search(r'ion-inline-start:"(/[^"]*/)src/pages/chat/chat\.html"', code)
    root = m.group(1) if m else STOCK_BUILD_ROOT
    return [(old.replace(STOCK_BUILD_ROOT, root), new.replace(STOCK_BUILD_ROOT, root))
            for old, new in JS_EDITS]


def patch_js(path):
    """Apply JS_EDITS to 2.js; returns False if the stock text is not there."""
    with open(path, encoding='utf-8', newline='') as f:
        code = f.read()
    edits = edits_for(code)
    if all(new in code for _, new in edits):
        print('2.js chat page already patched')
        return True
    if any(new not in code and code.count(old) != 1 for old, new in edits):
        print('2.js: expected stock text not found - not patched')
        return False
    for old, new in edits:
        if new not in code:
            code = code.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(code)
    print('2.js chat page patched')
    return True


def patch_css(path):
    """Append CSS_BLOCK to main.css once."""
    with open(path, encoding='utf-8', newline='') as f:
        css = f.read()
    if CSS_MARKER in css:
        print('main.css chat styles already present')
        return True
    if css and not css.endswith('\n'):
        css += '\n'
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(css + CSS_BLOCK)
    print('main.css chat styles added')
    return True


if __name__ == '__main__':
    ok = patch_js(os.path.join(BUILD, '2.js'))
    ok = patch_css(os.path.join(BUILD, 'main.css')) and ok
    sys.exit(0 if ok else 1)
