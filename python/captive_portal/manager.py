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


def is_android_cpa_requiring_204():
    """Does this captive portal agent need a 204 during its lifecycle?

    Android 7 and 8 CPAs fallback to cellular if they don't receive
    a 204 (and this generally manifests as broken DNS within the
    user's regular browser). Earlier Android CPAs will not fallback
    to cellular under these conditions, and indeed will close any
    open captive portal browsers if they receive a 204
    """
    ua_str = request.headers.get("User-agent", "")
    user_agent = user_agent_parser.Parse(ua_str)
    # Android CPBs all advertise themselves as Android
    # Android CPAs for <= v7 are Dalvik.
    # Android CPAs for v8 (and above?) don't even
    #  list themselves as Android, but if we're here
    #  we're (very likely to be) on an Android platform
    #  so we can assume that the lack of Android in the
    #  user agent string indicates that we're a v8 CPA.
    if user_agent["os"]["family"] != "Android":
        # We're a v8 CPA.
        return True

    if user_agent["os"]["family"] == "Android" and \
            user_agent["os"]["major"] == "7" and \
            "Dalvik" in ua_str:
        return True

    return False


def register_client(ip_addr_str):
    _client_map[ip_addr_str] = datetime.datetime.now()


def update_client_last_seen(ip_addr_str):
    _client_map[ip_addr_str] = datetime.datetime.now()


def register_and_show_connected():
    ip_addr_str = request.headers["X-Forwarded-For"]
    register_client(ip_addr_str)
    return show_connected()

def register_or_give_204():
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_registered_client(source_ip):
        update_client_last_seen(source_ip)
        return Response(status=204)

    return register_and_show_connected()


def show_success_or_show_connected():
    source_ip = request.headers["X-Forwarded-For"]
    if is_recent_registered_client(source_ip):
        update_client_last_seen(source_ip)
        return render_template("success.html")

    return register_and_show_connected()


def handle_ios_macos():
    """Handle iOS and MacOS interactions
    iOS <v9 and MacOS pre-yosemite
    See: https://forum.piratebox.cc/read.php?9,8927

    iOS >= v9 and MacOS Yosemite and later:
    # pylint: disable=line-too-long
    See: https://apple.stackexchange.com/questions/45418/how-to-automatically-login-to-captive-portals-on-os-x
    """
    ua_str = request.headers.get("User-agent", "")
    if "CaptiveNetworkSupport" in ua_str:
        # CaptiveNetworkSupport/wispr is the captive portal agent.
        # Always show "success" after initial interaction
        return show_success_or_show_connected()

    # We're the captive portal browser.
    # Show connected message after initial interaction
    return register_and_show_connected()


def handle_android():
    """Handle Android interactions"""
    if is_android_cpa_requiring_204():
        # We only want to send a 204 to some Android CPAs
        #  given <= v6 close CPB sessions when they receive
        #  a 204, and the CPB session is the way that we provide
        #  instructions on how to get to content
        return register_or_give_204()

    return show_connected()


def remove_authorised_client():
    """Forgets that a client has been seen recently to allow running tests"""
    source_ip = request.headers["X-Forwarded-For"]
    if source_ip in _client_map:
        del _client_map[source_ip]

    return Response(status=204)


def handle_wifistub_html():
    return show_connected()


def handle_ncsi_txt():
    return show_connected()


def show_connected():
    ua_str = request.headers.get("User-agent", "")
    return render_template(
        "connected.html",
        connectbox_url=get_real_connectbox_url(),
        LINK_OPS=LINK_OPS,
        link_type=get_link_type(ua_str),
    )


def setup_captive_portal_app(cpm):
    # Captive Portal Check for iOS <v9 and MacOS pre-yosemite
    cpm.add_url_rule('/success.html',
                     'handle_ios_macos',
                     handle_ios_macos)
    # iOS from captive portal
    cpm.add_url_rule('/library/test/success.html',
                     'handle_ios_macos',
                     handle_ios_macos)
    # Captive portal check for iOS >= v9 and MacOS Yosemite and later
    cpm.add_url_rule('/hotspot-detect.html',
                     'handle_ios_macos',
                     handle_ios_macos)
    # Android <= v6 (possibly later too)
    # pylint: disable=line-too-long
    # See: https://www.chromium.org/chromium-os/chromiumos-design-docs/network-portal-detection
    cpm.add_url_rule('/generate_204',
                     'handle_android',
                     handle_android)
    # Fallback method introduced in Android 7
    # pylint: disable=line-too-long
    # See: https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/connectivity/NetworkMonitor.java#92
    cpm.add_url_rule('/gen_204',
                     'handle_android',
                     handle_android)
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
                     'auth', register_and_show_connected, methods=['POST'])
    cpm.add_url_rule('/_authorised_clients',
                     'deauth', remove_authorised_client, methods=['DELETE'])
    cpm.add_url_rule('/_redirect_to_connectbox',
                     'redirect', redirect_to_connectbox)
    cpm.wsgi_app = ProxyFix(cpm.wsgi_app)
