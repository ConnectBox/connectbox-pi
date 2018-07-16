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
import functools
import os.path
import requests
from flask import redirect, render_template, request, Response
from ua_parser import user_agent_parser
from werkzeug.contrib.fixers import ProxyFix

LINK_OPS = {
    "TEXT": "text",
    "HREF": "href",
}
# pylint: disable=invalid-name
_client_map = {}
DHCP_FALLBACK_LEASE_SECS = 86400  # 1 day
REAL_HOST_REDIRECT_URL = "http://127.0.0.1/to-hostname"


def redirect_to_connectbox():
    # Redirect to connectbox, but don't authorise. We don't want to
    #  authorise because it'll interfere with the client-specific
    #  authorisation workflow. We assume that the client-specific
    #  workflow will be done separately.
    return redirect(get_real_connectbox_url())


@functools.lru_cache()
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


@functools.lru_cache()
def get_dhcp_lease_secs():
    """Extract lease time from /etc/dnsmasq.conf

    dhcp-range=10.129.0.2,10.129.0.250,255.255.255.0,300
    """
    # So we have a valid lease time if we can't parse the file for
    #  some reason (this shouldn't ever be necessary)
    dhcp_lease_secs = DHCP_FALLBACK_LEASE_SECS
    dnsmasq_file = "/etc/dnsmasq.conf"
    if os.path.isfile(dnsmasq_file):
        with open(dnsmasq_file) as dnsmasq_conf:
            for line in dnsmasq_conf:
                if line[:10] == "dhcp_range":
                    dhcp_lease_secs = int(line.split(",")[-1])
    return dhcp_lease_secs


def is_recent_registered_client(ip_addr_str):
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

    if user_agent["os"]["family"] == "Mac OS X" and \
            user_agent["os"]["major"] == "10" and \
            user_agent["os"]["minor"] == "12":
        # Sierra (10.12) can open links from the captive portal agent in
        #  the browser
        return LINK_OPS["HREF"]

    if user_agent["os"]["family"] == "Android" and \
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
    if is_recent_registered_client(source_ip):
        # Update last-seen time
        register_client(source_ip)
        return render_template(template)

    return add_authorised_client()


def handle_success_html():
    """Captive Portal Check for iOS <v9 and MacOS pre-yosemite

    See: https://forum.piratebox.cc/read.php?9,8927
    No need to check for user agent, because the default server does not serve
    the connectbox interface, so we don't need to avoid name clashes.
    """
    return welcome_or_serve_template("success.html")


def handle_hotspot_detect_html():
    """Captive portal check for iOS >= v9 and MacOS Yosemite and later

    # pylint: disable=line-too-long
    See: https://apple.stackexchange.com/questions/45418/how-to-automatically-login-to-captive-portals-on-os-x
    """
    ua_str = request.headers.get("User-agent", "")
    # wispr is the captive portal agent.
    if "wispr" in ua_str:
        return welcome_or_serve_template("success.html")

    return add_authorised_client()


def remove_authorised_client(ip_addr_str=None):
    """Forgets that a client has been seen recently to allow running tests"""
    if ip_addr_str:
        source_ip = ip_addr_str
    else:
        source_ip = request.headers["X-Forwarded-For"]

    if source_ip in _client_map:
        del _client_map[source_ip]

    return Response(status=204)


def handle_wifistub_html():
    return show_captive_portal_welcome()


def handle_ncsi_txt():
    return show_captive_portal_welcome()


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
                     handle_success_html)
    # iOS from captive portal
    cpm.add_url_rule('/library/test/success.html',
                     'success',
                     handle_success_html)
    cpm.add_url_rule('/hotspot-detect.html',
                     'hotspot-detect',
                     handle_hotspot_detect_html)
    # Android <= v6 (possibly later too)
    # pylint: disable=line-too-long
    # See: https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection
    cpm.add_url_rule('/generate_204',
                     'welcome',
                     show_captive_portal_welcome)
    # Fallback method introduced in Android 7
    # pylint: disable=line-too-long
    # See: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java#92
    cpm.add_url_rule('/gen_204',
                     'welcome',
                     show_captive_portal_welcome)
    # Captive Portal check for Amazon Kindle Fire
    cpm.add_url_rule('/kindle-wifi/wifistub.html',
                     'handle_wifistub_html',
                     handle_wifistub_html)
    # Captive Portal check for Windows
    # See: https://technet.microsoft.com/en-us/library/cc766017(v=ws.10).aspx
    cpm.add_url_rule('/ncsi.txt',
                     'handle_ncsi_txt',
                     handle_ncsi_txt)
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
