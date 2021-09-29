import os
from six.moves import configparser

from flask import Flask
from chat.server import register as register_chat
from admin.api import register as register_admin

# Ubuntu CI may not have locale set (see #134)
import locale
if locale.getlocale()[1] != "UTF-8":
    local_lang = locale.getlocale()[0]
    if local_lang is None:
        locale.setlocale(locale.LC_ALL, "C.UTF-8")
    else:
        locale.setlocale(locale.LC_ALL, local_lang + ".UTF-8")


config_parser = configparser.ConfigParser()
config_parser.readfp(open('%s/defaults.cfg' % os.path.dirname(os.path.abspath(__file__))))
config_parser.read(['/usr/local/connectbox/etc/connectbox.conf'])

DATABASE_DIRECTORY = config_parser.get('main', 'DATABASE_DIRECTORY')

def chat_connection_info():
    """ get db connection info string """
    return 'sqlite:///%s/cbchat.db' % (DATABASE_DIRECTORY)

app = Flask(__name__)

register_chat(app, chat_connection_info)
register_admin(app)

# @app.route('/foo')
# def foo():
#     return jsonify({'tasks': ['a','b','c']})

if __name__ == "__main__":
    # XXX debug should be off for non-development releases
    app.run(host='0.0.0.0', port=5000, debug=True)
