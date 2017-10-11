import datetime
import threading
import time
import requests
from flask import Flask, redirect, render_template, request, Response
from ua_parser import user_agent_parser
from werkzeug.contrib.fixers import ProxyFix

LINK_OPS = {
    "TEXT": "text",
    "HREF": "href",
    "JS_DOC_LOC_HREF": "javascript_document_location_href",
    "JS_WIN_LOC_HREF": "javascript_window_location_href",
    "JS_WIN_OPEN": "javascript_window_open",
    "JS_WIN_OPEN_BLANK": "javascript_window_open_blank",
    "JS_HREF_NORMAL_CLICK": "javascript_href_normal_click",
    "JS_HREF_BLANK_CLICK": "javascript_href_blank_click",
}
_client_map = {}
_delayed_registration_times = {}
ANDROID_V6_REGISTRATION_DELAY_SECS = 180
DHCP_FALLBACK_LEASE_SECS = 86400  # 1 day
REAL_HOST_REDIRECT_URL = "http://127.0.0.1/to-hostname"


def redirect_to_connectbox():
    # Redirect to connectbox, but don't authorise. We don't want to
    #  authorise because it'll interfere with the client-specific
    #  authorisation workflow. We assume that the client-specific
    #  workflow will be done separately.
    return redirect(_real_connectbox_url)


def get_real_connectbox_url():
    """Get the hostname where the connectbox can be found

    We could remove the need for this if we had a redirect in nginx from
    the default vhost to the connectbox host but that would mean putting
    an ugly URL like http://a.b.c.d/some-redirect in the captive portal
    page. So we use the value from that redirect to present a nice URL.
    """
    resp = requests.get(REAL_HOST_REDIRECT_URL,
                        allow_redirects=False)
    return resp.headers["Location"]


def get_dhcp_lease_secs():
    """Extract lease time from /etc/dnsmasq.conf

    dhcp-range=10.129.0.2,10.129.0.250,255.255.255.0,300
    """
    # So we have a valid lease time if we can't parse the file for
    #  some reason (this shouldn't ever be necessary)
    _dhcp_lease_secs = DHCP_FALLBACK_LEASE_SECS
    with open("/etc/dnsmasq.conf") as dnsmasq_conf:
        for line in dnsmasq_conf:
            if line[:10] == "dhcp_range":
                _dhcp_lease_secs = int(line.split(",")[-1])
    return _dhcp_lease_secs


def is_authorised_client(ip_addr_str):
    diff_client_recency_criteria = \
            datetime.timedelta(seconds=get_dhcp_lease_secs())
    last_registered_time = _client_map.get(ip_addr_str)
    if last_registered_time:
        time_since_reg = datetime.datetime.now() - last_registered_time
        return time_since_reg < diff_client_recency_criteria
    return False


def get_link_type(ua_str):
    user_agent = user_agent_parser.Parse(ua_str)
    if user_agent["os"]["family"] == "iOS" and \
            user_agent["os"]["major"] == "9":
        # iOS 9 can open links from the captive portal agent in the browser
        return LINK_OPS["HREF"]
    elif user_agent["os"]["family"] == "Mac OS X" and \
            user_agent["os"]["major"] == "10" and \
            user_agent["os"]["minor"] == "12":
        # Sierra (10.12) can open links from the captive portal agent in
        #  the browser
        return LINK_OPS["HREF"]
    elif user_agent["os"]["family"] == "Android" and \
            (user_agent["os"]["major"] == "5" or
             user_agent["os"]["major"] == "6"):
        # Lollipop (Android v5) and Marshmallow (Android v6) can render links,
        #  and can execute javascript but all operations keep the device
        #  trapped in the reduced-capability captive portal browsers and we
        #  don't want that, so we just show text
        return LINK_OPS["TEXT"]

    return LINK_OPS["TEXT"]


def authorise_client(ip_addr_str=None, delay_seconds=0):
    if ip_addr_str is None:
        ip_addr_str = request.headers["X-Forwarded-For"]

    if delay_seconds == 0:
        # Just do it
        register_client(ip_addr_str)
    else:
        # Don't allow more than one delayed registration per IP address
        #  (don't run the risk of DoS'ing the server)
        reg_time = _delayed_registration_times.get(ip_addr_str, 0)
        if reg_time <= time.time():
            # We don't have a pending registration so schedule one
            _delayed_registration_times[ip_addr_str] = time.time()
            t = threading.Timer(delay_seconds,
                                register_client,
                                args=[ip_addr_str])
            t.start()

    return render_template("connected.html",
                           connectbox_url=get_real_connectbox_url(),
                           LINK_OPS=LINK_OPS,
                           link_type=get_link_type(
                               request.headers.get("User-agent", "")))


def register_client(ip_addr_str):
    # Remove any delayed registration timestamps so we don't leak
    try:
        del _delayed_registration_times[ip_addr_str]
    except KeyError:
        pass

    # Now register
    _client_map[ip_addr_str] = datetime.datetime.now()


def welcome_or_serve_template(template):
    source_ip = request.headers["X-Forwarded-For"]
    if is_authorised_client(source_ip):
        register_client(source_ip)
        return render_template(template)

    return authorise_client()


def cp_check_ios_lt_v9_macos_lt_v1010():
    """Captive Portal Check for iOS and MacOS pre-yosemite

    See: https://forum.piratebox.cc/read.php?9,8927
    No need to check for user agent, because the default server does not serve
    the connectbox interface, so we don't need to avoid name clashes.
    """
    return welcome_or_serve_template("success.html")


def cp_check_ios_gte_v9_macos_gte_v1010():
    """Captive portal check for MacOS Yosemite and later

    # noqa (ignore line length check for URLs)
    See: https://apple.stackexchange.com/questions/45418/how-to-automatically-login-to-captive-portals-on-os-x

    No need to check for user agent, because the default server does not serve
    the connectbox interface, so we don't need to avoid name clashes.
    """
    ua_str = request.headers.get("User-agent", "")
    if "wispr" in ua_str:
        return welcome_or_serve_template("hotspot-detect.html")

    return authorise_client()


def cp_check_status_no_content():
    """Captive Portal Check for devices and apps wanting a 204

    # noqa (ignore line length check for URLs)

    generate_204 is a standard Android check
    See: https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection

    gen_204 is a fallback method introduced in Android 7
    See: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java#92

    /mobile/status.php satisfies facebook messenger connectivity check
    """
    source_ip = request.headers["X-Forwarded-For"]
    ua_str = request.headers.get("User-agent", "")
    user_agent = user_agent_parser.Parse(ua_str)
    # Android uses a Dalvik agent for captive portal detection, but uses
    #  a Chrome webview to display the welcome/terms page so we want to
    #  return a web page only when we get a request from that Chrome view
    # We don't need to check whether the user is authorised because they
    #  will only get prompted to sign into the network when they don't
    #  get a 204 response at some stage in the recent past
    if user_agent["os"]["family"] == "Android" and \
            user_agent["user_agent"]["family"] == "Chrome" and \
            user_agent["os"]["major"] == "5":
        return render_template(
            "connected.html",
            connectbox_url=get_real_connectbox_url(),
            LINK_OPS=LINK_OPS,
            link_type=get_link_type(ua_str),
            ua_str=ua_str,
            req_url=request.url,
        )

    # XXX - temporarily comment out this block, and make the above block
    #       apply to android 5 only, while we sort out a workflow that works
    #       reliably for non v5 android versions.
    # Android 6 and above automatically close the captive portal browser
    #  once a 204 is received, so we kick off a timer to authorise the
    #  client after a little while, and provide 200 responses until then.
    # Note that this check only applies to the Dalvik captive portal
    #  checker, not the webview
    # XXX robustificate pls in the face of missing fields (or check whether
    #  the user agent parser robustificates for us
    # if user_agent["user_agent"]["family"] == "Android" and \
    #         int(user_agent["user_agent"]["major"]) >= 6:
    #     # schedule delayed registration
    #     delay_registration_seconds = ANDROID_V6_REGISTRATION_DELAY_SECS
    # else:
    #     delay_registration_seconds = 0
    delay_registration_seconds = 0

    if is_authorised_client(source_ip):
        return Response(status=204)

    return authorise_client(source_ip, delay_registration_seconds)


def cp_check_amazon_kindle_fire():
    """Captive portal check for Amazon Kindle Fire
    """
    return welcome_or_serve_template("wifistub.html")


def cp_check_windows():
    """Captive portal check for Windows

    See: https://technet.microsoft.com/en-us/library/cc766017(v=ws.10).aspx
    """
    return welcome_or_serve_template("ncsi.txt")


def forget_client():
    """Forgets that a client has been seen recently to allow running tests"""
    # XXX how can we unschedule delayed registrations
    source_ip = request.headers["X-Forwarded-For"]
    if source_ip in _client_map:
        del _client_map[source_ip]

    # Is this an acceptable status code?
    return Response(status=204)


def setup_captive_portal_app():
    cpm = Flask(__name__)
    cpm.add_url_rule('/',
                     'index', redirect_to_connectbox)
    cpm.add_url_rule('/success.html',
                     'success',
                     cp_check_ios_lt_v9_macos_lt_v1010)
    # iOS from captive portal
    cpm.add_url_rule('/library/test/success.html',
                     'success',
                     cp_check_ios_lt_v9_macos_lt_v1010)
    cpm.add_url_rule('/hotspot-detect.html',
                     'hotspot-detect', cp_check_ios_gte_v9_macos_gte_v1010)
    cpm.add_url_rule('/generate_204',
                     'generate_204', cp_check_status_no_content)
    cpm.add_url_rule('/gen_204',
                     'gen_204', cp_check_status_no_content)
    cpm.add_url_rule('/mobile/status.php',
                     'status', cp_check_status_no_content)
    cpm.add_url_rule('/kindle-wifi/wifistub.html',
                     'kindle-wifi', cp_check_amazon_kindle_fire)
    cpm.add_url_rule('/ncsi.txt',
                     'ncsi', cp_check_windows)
    cpm.add_url_rule('/_authorise_client',
                     'auth', authorise_client, methods=['POST'])
    cpm.add_url_rule('/_authorise_client/<ip_addr_str>',
                     'auth_ip', authorise_client, methods=['POST'])
    cpm.add_url_rule('/_forget_client',
                     'forget', forget_client)
    cpm.wsgi_app = ProxyFix(cpm.wsgi_app)
    return cpm


app = setup_captive_portal_app()  # pylint: disable=C0103
_real_connectbox_url = get_real_connectbox_url()
_dhcp_lease_secs = get_dhcp_lease_secs()


# There's no simple way to set an error handler without using a decorator
#  but that requires app to be defined at the top level, and before use of
#  the decorator.
@app.errorhandler(404)
def default_view(_):
    """Handle all URLs and send them to the welcome page"""
    return redirect_to_connectbox()


if __name__ == "__main__":
    # XXX debug should be off for non-development releases
    app.run(host='0.0.0.0', debug=True)
