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

import functools
import os.path
import time
import requests
from flask import redirect, render_template, request, Response
from ua_parser import user_agent_parser
from werkzeug.contrib.fixers import ProxyFix

LINK_OPS = {
    "TEXT": "text",
    "HREF": "href",
}
# pylint: disable=invalid-name
_last_captive_portal_session_start_time = {}
DHCP_FALLBACK_LEASE_SECS = 86400  # 1 day
MAX_ASSUMED_CP_SESSION_TIME_SECS = 300
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


def secs_since_last_session_start():
    ip_addr_str = request.headers["X-Forwarded-For"]
    last_session_start_time = \
        _last_captive_portal_session_start_time.get(ip_addr_str, 0)
    return time.time() - last_session_start_time


def client_is_rejoining_network():
    """
    Checks whether this IP has gone through this CP recently

    We want to avoid bringing up the captive portal browser when a
    user rejoins the network after a short break because spamminess
    is bad, and they shouldn't need a pointer to the content (which
    is what the captive portal browser provides).

    We differentiate rejoining the network as opposed to continuing the
    same captive portal session, and we do this by saying that a rejoin
    is only happening if it's more than MAX_ASSUMED_CP_SESSION_TIME_SECS
    after the last session started

    We base our recency criteria on the DHCP lease time
    """
    max_time_without_showing_cp = get_dhcp_lease_secs()
    secs_since_last_sess_start = secs_since_last_session_start()
    return secs_since_last_sess_start < max_time_without_showing_cp and \
        secs_since_last_sess_start > MAX_ASSUMED_CP_SESSION_TIME_SECS


def is_new_captive_portal_session():
    return secs_since_last_session_start() > MAX_ASSUMED_CP_SESSION_TIME_SECS

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


def android_cpa_needs_204_now():
    """Does this captive portal agent need a 204 right now?

    Android 7 and 8 CPAs fallback to cellular if they don't receive
    a 204 (and this generally manifests as broken DNS within the
    user's regular browser). Earlier Android CPAs will not fallback
    to cellular under these conditions

    Android 7 and earlier close the CBP when they receive a 204,
    so we don't want to do that if we don't have to, and if we must
    then we maximise the time that the user can see the CPA.
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
        # We're a v8 CPA. OK to send a 204 anytime
        return True

    if user_agent["os"]["family"] == "Android" and \
            user_agent["os"]["major"] == "7" and \
            "Dalvik" in ua_str:
        # XXX explain why
        # XXX unmagic this number
        return secs_since_last_session_start() > 20

    # Never send a 204
    return False


def register_captive_portal_session_start():
    ip_addr_str = request.headers["X-Forwarded-For"]
    last = _last_captive_portal_session_start_time.get(ip_addr_str, 0)
    if last < time.time() - MAX_ASSUMED_CP_SESSION_TIME_SECS:
        # Treat as a new session and update session start time
        _last_captive_portal_session_start_time[ip_addr_str] = \
            time.time()


def register_and_show_connected():
    return show_connected()

def register_or_give_204():
    if client_is_rejoining_network():
        return Response(status=204)

    return register_and_show_connected()


def show_success_or_show_connected():

    return register_and_show_connected()


def handle_ios_macos():
    """Handle iOS and MacOS interactions
    iOS <v9 and MacOS pre-yosemite
    See: https://forum.piratebox.cc/read.php?9,8927

    iOS >= v9 and MacOS Yosemite and later:
    # pylint: disable=line-too-long
    See: https://apple.stackexchange.com/questions/45418/how-to-automatically-login-to-captive-portals-on-os-x
    """
    if client_is_rejoining_network():
        # Don't raise captive portal browser
        register_captive_portal_session_start()
        return render_template("success.html")

    if is_new_captive_portal_session():
        register_captive_portal_session_start()
        # raise captive portal browser by not showing success.html
        return show_connected()

    ua_str = request.headers.get("User-agent", "")
    if "CaptiveNetworkSupport" in ua_str:
        # CaptiveNetworkSupport/wispr is the captive portal agent.
        # Always show "success" after initial interaction
        return render_template("success.html")

    # We're the captive portal browser.
    # Show connected message after initial interaction
    return show_connected()


def handle_android():
    """Handle Android interactions"""
    if client_is_rejoining_network():
        # Don't raise captive portal browser
        register_captive_portal_session_start()
        return Response(status=204)

    if is_new_captive_portal_session():
        register_captive_portal_session_start()
        # raise captive portal browser by not providing a 204
        return show_connected()

    if android_cpa_needs_204_now():
        # We only want to send a 204 to some Android CPAs
        #  and only under certain circumstances
        return Response(status=204)

    return show_connected()


def remove_authorised_client():
    """Forgets that a client has been seen recently to allow running tests"""
    source_ip = request.headers["X-Forwarded-For"]
    if source_ip in _last_captive_portal_session_start_time:
        del _last_captive_portal_session_start_time[source_ip]

    return Response(status=204)


def handle_wifistub_html():
    register_captive_portal_session_start()
    return show_connected()


def handle_ncsi_txt():
    register_captive_portal_session_start()
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
