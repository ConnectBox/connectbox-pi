"""
A limited Captive Portal implementation

Does the minimum required to:
* Get basic instructions in front of the user about where to find content,
  using the device's default captive portal viewer.
* Allow the user to stay joined to the ConnectBox AP (on some devices,
  we must provide responses to indicate that the ConnectBox provides
  internet access, otherwise the captive portal viewer will not allow
  the user to remain joined to the network)
* Prevent the user from attempting to browse ConnectBox content in the
  reduced-functionality captive portal browser (CP browsers vary across
  devices, but can lack important functionality like javascript, video
  and audio players and PDF viewing).
"""

import datetime
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
DHCP_FALLBACK_LEASE_SECS = 86400  # 1 day
REAL_HOST_REDIRECT_URL = "http://127.0.0.1/to-hostname"
_real_connectbox_url = None


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
    global _real_connectbox_url
    if not _real_connectbox_url:
        resp = requests.get(REAL_HOST_REDIRECT_URL,
                            allow_redirects=False)
        _real_connectbox_url = resp.headers["Location"]
    return _real_connectbox_url


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


def is_recent_authorised_client(ip_addr_str):
    """
    Checks whether this IP has gone through this CP recently

    We want to avoid bringing up the captive portal browser when a
    user rejoins the network after a short break because spamminess
    is bad, and they shouldn't need a pointer to the content (which
    is what the captive portal browser provides).

    We base our recency criteria on the DHCP lease time
    """
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


def add_authorised_client(ip_addr_str=None):
    if ip_addr_str is None:
        ip_addr_str = request.headers["X-Forwarded-For"]

    register_client(ip_addr_str)
    return show_captive_portal_welcome()


def register_client(ip_addr_str):
    _client_map[ip_addr_str] = datetime.datetime.now()


def welcome_or_serve_template(template):
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_authorised_client(source_ip):
        # Update last-seen time
        register_client(source_ip)
        return render_template(template)

    return add_authorised_client()


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
        return welcome_or_serve_template("success.html")

    return add_authorised_client()


def remove_authorised_client(ip_addr_str=None):
    """Forgets that a client has been seen recently to allow running tests"""
    source_ip = request.headers["X-Forwarded-For"]
    if source_ip in _client_map:
        del _client_map[source_ip]

    return Response(status=204)


def show_captive_portal_welcome():
    ua_str = request.headers.get("User-agent", "")
    return render_template(
        "connected.html",
        connectbox_url=get_real_connectbox_url(),
        LINK_OPS=LINK_OPS,
        link_type=get_link_type(ua_str),
    )


def setup_captive_portal_app(cpm):
    cpm.add_url_rule('/success.html',
                     'success',
                     cp_check_ios_lt_v9_macos_lt_v1010)
    # iOS from captive portal
    cpm.add_url_rule('/library/test/success.html',
                     'success',
                     cp_check_ios_lt_v9_macos_lt_v1010)
    cpm.add_url_rule('/hotspot-detect.html',
                     'hotspot-detect', cp_check_ios_gte_v9_macos_gte_v1010)
    # Android <= v6 (possibly later too)
    # noqa: See: https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection
    cpm.add_url_rule('/generate_204', 'welcome',
                     show_captive_portal_welcome)
    # Fallback method introduced in Android 7
    # See:
    # noqa: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java#92
    cpm.add_url_rule('/gen_204', 'welcome',
                     show_captive_portal_welcome)
    # Captive Portal check for Amazon Kindle Fire
    cpm.add_url_rule('/kindle-wifi/wifistub.html', 'welcome',
                     show_captive_portal_welcome)
    # Captive Portal check for Windows
    # See: https://technet.microsoft.com/en-us/library/cc766017(v=ws.10).aspx
    cpm.add_url_rule('/ncsi.txt', 'welcome',
                     show_captive_portal_welcome)
    # cpm.add_url_rule('/_authorised_clients',
    #                  'auth', get_authorised_clients, methods=['GET'])
    cpm.add_url_rule('/_authorised_clients',
                     'auth', add_authorised_client, methods=['POST'])
    cpm.add_url_rule('/_authorised_clients/<ip_addr_str>',
                     'auth_ip', add_authorised_client, methods=['PUT'])
    cpm.add_url_rule('/_authorised_clients',
                     'deauth', remove_authorised_client, methods=['DELETE'])
    cpm.add_url_rule('/_authorised_clients/<ip_addr_str>',
                     'deauth_ip', remove_authorised_client, methods=['DELETE'])
    cpm.add_url_rule('/_redirect_to_connectbox',
                     'redirect', redirect_to_connectbox)
    cpm.wsgi_app = ProxyFix(cpm.wsgi_app)

_dhcp_lease_secs = get_dhcp_lease_secs()
