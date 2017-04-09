import datetime
from flask import Flask, redirect, render_template, request, Response
from werkzeug.contrib.fixers import ProxyFix

WELCOME_TEMPLATE = "welcome.html"
_client_map = {}
REAL_HOST_REDIRECT_URL = "/to-hostname"
# XXX how do we get the dhcp lease time?
DHCP_LEASE_TIME = "5m"


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)


@app.route('/')
def cp_entry_point():
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_client(source_ip):
        return redirect(REAL_HOST_REDIRECT_URL)
    else:
        register_client(source_ip)
        return render_template(WELCOME_TEMPLATE)


def is_recent_client(ip_address_str):
    # XXX need timeout here too
    # XXX and purge
    return ip_address_str in _client_map


def register_client(ip_address_str):
    _client_map[ip_address_str] = datetime.datetime.now()


def welcome_or_serve_template(template):
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_client(source_ip):
        return render_template(template)
    else:
        register_client(source_ip)
        return render_template(WELCOME_TEMPLATE)


def welcome_or_return_status_code(status_code):
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_client(source_ip):
        return Response(status=status_code)
    else:
        register_client(source_ip)
        return render_template(WELCOME_TEMPLATE)


@app.route('/success.html')
def cp_check_ios_macos_pre_yosemite():
    """Captive Portal Check for iOS and MacOS pre-yosemite

    See: https://forum.piratebox.cc/read.php?9,8927
    No need to check for user agent, because the default server does not serve
    the connectbox interface, so we don't need to avoid name clashes.
    """
    return welcome_or_serve_template("success.html")


@app.route('/hotspot-detect.html')
def cp_check_macos_post_yosemite():
    """Captive portal check for MacOS Yosemite and later

    # noqa (ignore line length check for URLs)

    See: https://apple.stackexchange.com/questions/45418/how-to-automatically-login-to-captive-portals-on-os-x
    No need to check for user agent, because the default server does not serve
    the connectbox interface, so we don't need to avoid name clashes.
    """
    return welcome_or_serve_template("hotspot-detect.html")


@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/mobile/status.php')
def cp_check_status_no_content():
    """Captive Portal Check for devices and apps wanting a 204

    # noqa (ignore line length check for URLs)

    generate_204 is a standard Android check
    See: https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection

    gen_204 is a fallback method introduced in Android 7
    See: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java#92

    /mobile/status.php satisfies facebook messenger connectivity check
    """
    return welcome_or_return_status_code(204)


@app.route('/kindle-wifi/wifistub.html')
def cp_check_amazon_kindle_fire():
    """Captive portal check for Amazon Kindle Fire
    """
    return welcome_or_serve_template("wifistub.html")


@app.route('/ncsi.txt')
def cp_check_windows():
    """Captive portal check for Windows

    See: https://technet.microsoft.com/en-us/library/cc766017(v=ws.10).aspx
    """
    return welcome_or_serve_template("ncsi.txt")


@app.route('/_forget_client')
def forget_client():
    """Forgets that a client has been seen recently to allow running tests"""
    source_ip = request.headers["X-Forwarded-For"]
    if source_ip in _client_map:
        del _client_map[source_ip]

    # XXX Is this an acceptable status code?
    return Response(status=204)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
