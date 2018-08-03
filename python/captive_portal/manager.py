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

import time
import requests
from flask import redirect, render_template, request, Response, url_for
from ua_parser import user_agent_parser
from werkzeug.contrib.fixers import ProxyFix

LINK_OPS = {
    "TEXT": "text",
    "HREF": "href",
}
# pylint: disable=invalid-name
_last_captive_portal_session_start_time = {}
MAX_ASSUMED_CP_SESSION_TIME_SECS = 300
MAX_TIME_WITHOUT_SHOWING_CP_SECS = 86400  # 1 day
ANDROID_7_CPA_MAX_SECS_WITHOUT_204 = 30


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
    secs_since_last_sess_start = secs_since_last_session_start()
    return secs_since_last_sess_start < MAX_TIME_WITHOUT_SHOWING_CP_SECS and \
        secs_since_last_sess_start > MAX_ASSUMED_CP_SESSION_TIME_SECS


def is_new_captive_portal_session():
    return secs_since_last_session_start() > MAX_ASSUMED_CP_SESSION_TIME_SECS


def get_link_type(ua_str):
    """Return whether the device can show useable hrefs


    Lollipop (Android v5) and Marshmallow (Android v6) can render links,
     and can execute javascript but all operations keep the device
     trapped in the reduced-capability captive portal browsers and we
     don't want that, so we just show text
    """
    user_agent = user_agent_parser.Parse(ua_str)
    if user_agent["os"]["family"] == "iOS" and \
            user_agent["os"]["major"] in ("9", "11"):
        # iOS 9 and iOS 11 can open links from the captive portal browser
        #  in the system browser. iOS 10 cannot - the link opens in the
        #  captive portal browser itself.
        return LINK_OPS["HREF"]

    if user_agent["os"]["family"] == "Mac OS X" and \
            user_agent["os"]["major"] == "10" and \
       user_agent["os"]["minor"] in ("12", "13"):
        # Sierra (10.12) and High Sierra (10.13) can open links from the
        #  captive portal browser in the system browser
        return LINK_OPS["HREF"]

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
        # Android 7 needs to see a 204 within about 40 seconds of its
        #  initial captive portal request. If it doesn't see one, it'll
        #  fall back to cellular. Unfortauntely when it does see a 204
        #  it closes the CPB, thus removing access to our instructions
        #  that explain on how to find the content.
        # We want to give the user time to read the instructions in the
        #  cpb, but want to avoid the fallback to cellular, so we wait
        #  for a period that's less than 40 seconds.
        return secs_since_last_session_start() > \
            ANDROID_7_CPA_MAX_SECS_WITHOUT_204

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
    register_captive_portal_session_start()
    return show_connected()


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
    user_agent = user_agent_parser.Parse(ua_str)
    if user_agent["os"]["family"] == "iOS" or \
           user_agent["os"]["family"] == "Mac OS X":
        icon_type = "safari"
    else:
        icon_type = "chrome"

    browser_icon = \
        url_for('static', filename='go-animation-%s.gif' % (icon_type,))
    return render_template(
        "connected.html",
        connectbox_url="http://go",
        LINK_OPS=LINK_OPS,
        browser_icon=browser_icon,
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
    # Android <= v8 (possibly later too)
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
    cpm.add_url_rule('/_authorised_clients',
                     'auth', register_and_show_connected, methods=['POST'])
    cpm.add_url_rule('/_authorised_clients',
                     'deauth', remove_authorised_client, methods=['DELETE'])
    cpm.wsgi_app = ProxyFix(cpm.wsgi_app)
