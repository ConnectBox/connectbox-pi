import json
import os
import unittest
import random
import requests

TEST_IP_ENV_VAR = "TEST_IP"

# Default creds. Will need a way to override these when it changes
ADMIN_USER = "admin"
ADMIN_PASSWORD = "connectbox"
_testBaseURL = ""
# Text in the welcome template
WELCOME_TEMPLATE_TEXT_SAMPLE = "<TITLE>Connected to ConnectBox Wifi</TITLE>"
# Corresponds to the 302 in the nginx default vhost config
FINAL_302_PAGE_SUFFIX = "to-hostname"


def getTestTarget():
    try:
        return os.environ[TEST_IP_ENV_VAR]
    except KeyError:
        error_msg = "Set the %s environment variable" % \
            (TEST_IP_ENV_VAR,)
        raise RuntimeError(error_msg)


def getTestBaseURL():
    """Gets the ConnectBox base URL, solely from the IP address

    1. Deregister client to ensure correct state
    2. First request to register client
    3. Subsequent request to receive 302 back to nginx
    4. Final request that uses nginx to 302 to ConnectBox vhost
    5. Deregister client to ensure correct state for subsequent requests

    Steps 3 & 4 happen in one requests.get because it follow redirects
    """

    global _testBaseURL
    if not _testBaseURL:
        # Deregister
        requests.get("http://%s/_forget_client" %
                     (getTestTarget(),)).raise_for_status()
        # Register (no redirects given)
        r = requests.get("http://%s" % (getTestTarget(),),)
        r.raise_for_status()
        # bounce through the 302, and retrieve the base connectbox page
        r = requests.get("http://%s" % (getTestTarget(),),)
        r.raise_for_status()
        # and this is the ConnectBox base URL that we want
        _testBaseURL = r.url
        # Deregister the client, so that the test case that triggered
        #  this request starts with a clean slate
        requests.get("http://%s/_forget_client" %
                     (getTestTarget(),)).raise_for_status()
    return _testBaseURL


def getAdminBaseURL():
    return getTestBaseURL() + "/admin"


def getAdminAuth():
    return requests.auth.HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)


class ConnectBoxBasicTestCase(unittest.TestCase):

    def testContentResponseType(self):
        # URLs under content should return json
        r = requests.get("%s/content/" % (getTestBaseURL(),))
        r.raise_for_status()
        self.assertIsInstance(r.json(), list)

    def testAdminNeedsAuth(self):
        r = requests.get("%s/" % (getAdminBaseURL(),))
        # No raise_for_status because we're checking for a 401
        self.assertEquals(r.status_code, 401)

    def testAdminNoTrailingSlashRequired(self):
        r = requests.get("%s" % (getAdminBaseURL(),), auth=getAdminAuth())
        r.raise_for_status()
        self.assertIn("ConnectBox Admin Dashboard", r.text)

    def testAdminPageTitle(self):
        r = requests.get("%s/" % (getAdminBaseURL(),), auth=getAdminAuth())
        r.raise_for_status()
        self.assertIn("ConnectBox Admin Dashboard", r.text)

    def testTextInDocumentTitle(self):
        r = requests.get("%s/" % (getTestBaseURL(),))
        r.raise_for_status()
        self.assertIn("<title>ConnectBox</title>", r.text)


class ConnectBoxDefaultVHostTestCase(unittest.TestCase):
    """Behavioural tests for the Nginx default vhost"""

    def setUp(self):
        """Simulate first connection

        Make sure the ConnectBox doesn't think the client has connected
        before, so we can test captive portal behaviour
        """
        requests.get("http://%s/_forget_client" %
                     (getTestTarget(),)).raise_for_status()

    def tearDown(self):
        """Leave system in a clean state

        Make sure the ConnectBox won't think this client has connected
        before, regardless of whether the next connection is from a
        test, or from a normal browser or captive portal connection
        """
        requests.get("http://%s/_forget_client" %
                     (getTestTarget(),)).raise_for_status()

    def testBaseRedirect(self):
        """Two hits on the index redirects to ConnectBox"""
        r = requests.get("http://%s" % (getTestTarget(),),)
        r.raise_for_status()
        self.assertIn(WELCOME_TEMPLATE_TEXT_SAMPLE, r.text)
        r = requests.get("http://%s" % (getTestTarget(),),
                         allow_redirects=False)
        r.raise_for_status()
        self.assertTrue(r.is_redirect)
        self.assertEquals(getTestBaseURL(), r.headers["Location"])

    def testIOS9CaptivePortalResponse(self):
        """iOS9 ConnectBox connection workflow"""
        # 1. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        # This is the UA from iOS 9.2.1 but let's assume it's representative
        headers.update({"User-Agent": "CaptiveNetworkSupport-325.10.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 2. We provide response that indicates no internet, causing
        #   captive portal browser to be opened
        self.assertNotIn("<BODY>\nSuccess\n</BODY>", r.text)
        # 3. Device sends regular user agent request for hotspot-detect.html
        #    to serve as contents of captive portal browser window
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "Mozilla/5.0 (iPad; CPU OS 9_2_1 like"
                        " Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko)"
                        " Mobile/13D15"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 4. We send a welcome page, with a link to click
        self.assertIn("<a href='%s'" % (getTestBaseURL(),), r.text)
        # 5. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "CaptiveNetworkSupport-325.10.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 6. We provide response that indicates an internet connection which
        #    changes captive portal browser button to "Done" and allows the
        #    user to click on the link
        self.assertIn("<BODY>\nSuccess\n</BODY>", r.text)

    def testIOS10CaptivePortalResponse(self):
        """iOS10 ConnectBox connection workflow"""
        # 1. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        # This is the UA from iOS 10.3.1 but let's assume it's representative
        headers.update({"User-Agent": "CaptiveNetworkSupport-346.50.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 2. We provide response that indicates no internet, causing
        #   captive portal browser to be opened
        self.assertNotIn("<BODY>\nSuccess\n</BODY>", r.text)
        # 3. Device sends regular user agent request for hotspot-detect.html
        #    to serve as contents of captive portal browser window
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "Mozilla/5.0 (iPad; CPU OS 10_3_1 like"
                        " Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko)"
                        " Mobile/14E304"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 4. We send a welcome page, but no link because 10.3.1 doesn't allow
        #    exiting of the captive portal browser by clicking on a link. We
        #    do send a text URL for cutting and pasting
        self.assertNotIn("<a href=", r.text)
        self.assertIn(getTestBaseURL(), r.text)
        # 5. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "CaptiveNetworkSupport-346.50.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 6. We provide response that indicates an internet connection which
        #    changes captive portal browser button to "Done" and allows the
        #    user to click on the link
        self.assertIn("<BODY>\nSuccess\n</BODY>", r.text)

    def testSierraCaptivePortalResponse(self):
        """MacOS 10.12 ConnectBox connection workflow

        Expected to be the same as post yosemite"""
        # 1. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        # This is the UA from OS 10.12.4 but let's assume it's representative
        headers.update({"User-Agent": "CaptiveNetworkSupport-346.50.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 2. Connectbox provides response that indicates no internet, causing
        #   captive portal browser to be opened
        self.assertNotIn("<BODY>\nSuccess\n</BODY>", r.text)
        # 3. Device sends regular user agent request for hotspot-detect.html
        #    to serve as contents of captive portal browser window
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X"
                        " 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko)"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 4. Connectbox sends a welcome page, with a link to click
        self.assertIn("<a href='%s'" % (getTestBaseURL(),), r.text)
        # 5. Device sends wispr hotspot-detect.html request
        headers = requests.utils.default_headers()
        headers.update({"User-Agent": "CaptiveNetworkSupport-346.50.1 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 6. Connectbox provides response that indicates an internet
        #    connection which changes captive portal browser button to "Done"
        #    and allows the user to click on the link
        self.assertIn("<BODY>\nSuccess\n</BODY>", r.text)

    def testAndroid5CaptivePortalResponse(self):
        """Android 5 ConnectBox connection workflow
        """
        # Strictly this should be requesting
        #  http://clients3.google.com/generate_204 but answering requests for
        #  that site requires DNS mods, which can't be assumed for all
        #  people running these tests, so let's just poke for the page using
        #  the IP address of the server so we hit the default server, where
        #  this 204 redirection is active.
        # 1. Device sends generate_204 request
        headers = requests.utils.default_headers()
        # This is the UA from a Lenovo junk Android 5 tablet, but let's assume
        #  that it's representative of over Android 5 (lollipop) devices
        headers.update({"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 5.0.1; "
                        "Lenovo TB3-710F Build/LRX21M)"})
        r = requests.get("http://%s/generate_204" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 2. Connectbox provides response that indicates no internet
        self.assertEquals(r.status_code, 200)
        # 3. Device send another generate_204 request within a few seconds
        r = requests.get("http://%s/generate_204" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 4. Connectbox replies that internet access is available.
        self.assertEquals(r.status_code, 204)
        # 5. On receipt of a 204 soon after a 200, the device shows a
        #    "Sign-in to network" notification. Counter-intuitively, if the
        #    device continues to get 200 replies, it never shows this
        #    notification.
        #    We assume that the user responds to this notification, which
        #    causes the Android captive portal browser to send a request
        #    to the generate_204 URL
        headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 5.0.1; "
                        "Lenovo TB3-710F Build/LRX21M; wv) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Version/4.0 Chrome/45.0.2454.95 "
                        "Safari/537.36"})
        r = requests.get("http://%s/generate_204" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 6. Connectbox provides a response with a text-URL
        self.assertIn("<TITLE>Connected to ConnectBox Wifi</TITLE>", r.text)
        # No URLs, please
        self.assertNotIn("href=", r.text.lower())

    def testAndroid6CaptivePortalResponse(self):
        """Android 6 ConnectBox connection workflow
        """
        # Strictly this should be requesting
        #  http://clients3.google.com/generate_204 but answering requests for
        #  that site requires DNS mods, which can't be assumed for all
        #  people running these tests, so let's just poke for the page using
        #  the IP address of the server so we hit the default server, where
        #  this 204 redirection is active.
        # 1. Device sends generate_204 request
        headers = requests.utils.default_headers()
        # This is the UA from a Lenovo junk Android 5 tablet, but let's assume
        #  that it's representative of over Android 5 (lollipop) devices
        headers.update({"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 6.0.1; "
                        "Nexus 7 Build/MOB30X)"})
        r = requests.get("http://%s/generate_204" %
                         (getTestTarget(),), headers=headers)
        r.raise_for_status()
        # 2. Connectbox provides response that indicates no internet
        self.assertEquals(r.status_code, 200)
        # XXX FILL ME IN

    def testAndroid7FallbackCaptivePortalResponse(self):
        """Return a 204 status code to bypass Android captive portal login"""
        # Strictly this should be requesting
        #  http://clients3.google.com/gen_204 but answering requests for
        #  that site requires DNS mods, which can't be assumed for all
        #  people running these tests, so let's just poke for the page using
        #  the IP address of the server so we hit the default server, where
        #  this 204 redirection is active.
        r = requests.get("http://%s/gen_204" % (getTestTarget(),))
        r.raise_for_status()
        r = requests.get("http://%s/gen_204" % (getTestTarget(),))
        r.raise_for_status()
        self.assertEquals(r.status_code, 204)

    def testWindowsCaptivePortalResponse(self):
        """Return ncsi.txt to bypass windows captive portal login page"""
        r = requests.get("http://%s/ncsi.txt" % (getTestTarget(),))
        r.raise_for_status()
        r = requests.get("http://%s/ncsi.txt" % (getTestTarget(),))
        r.raise_for_status()
        self.assertEquals("Microsoft NCSI", r.text)

    def testAmazonKindleCaptivePortalResponse(self):
        """Return wifistub.html to bypass kindle captive portal login page"""
        r = requests.get("http://%s/kindle-wifi/wifistub.html" %
                         (getTestTarget(),))
        r.raise_for_status()
        r = requests.get("http://%s/kindle-wifi/wifistub.html" %
                         (getTestTarget(),))
        r.raise_for_status()
        self.assertIn("81ce4465-7167-4dcb-835b-dcc9e44c112a", r.text)

    def testFacebookMessengerConnectivityResponse(self):
        """Return 204 status code to bypass FB messenger connectivity check"""
        r = requests.get("http://%s/mobile/status.php" % (getTestTarget(),))
        r.raise_for_status()
        r = requests.get("http://%s/mobile/status.php" % (getTestTarget(),))
        r.raise_for_status()
        self.assertEquals(r.status_code, 204)

    def testUnknownLocalPageResponse(self):
        """Two hits on an unregistered local route redirects to ConnectBox"""
        r = requests.get("http://%s/unknown_local_page" % (getTestTarget(),))
        r.raise_for_status()
        self.assertIn(WELCOME_TEMPLATE_TEXT_SAMPLE, r.text)
        r = requests.get("http://%s/unknown_local_page" % (getTestTarget(),),
                         allow_redirects=False)
        r.raise_for_status()
        self.assertTrue(r.is_redirect)
        self.assertEquals(getTestBaseURL(), r.headers["Location"])

    @unittest.skip("Workflow unclear atm")
    def testUnknownNonLocalPageResponse(self):
        """Two hits on an unregistered remote route redirects to ConnectBox"""
        req = requests.Request(
            "GET",
            "http://%s/unknown_non_local_page" % (getTestTarget(),)
        )
        req.headers["Host"] = "non-local-host.com"
        s = requests.Session()
        r = s.send(req.prepare())
        r.raise_for_status()
        self.assertIn(WELCOME_TEMPLATE_TEXT_SAMPLE, r.text)
        #XXX Unsure why this second request is failing
        #req = requests.Request(
        #    "GET",
        #    "http://%s/unknown_non_local_page" % (getTestTarget(),)
        #)
        #req.headers["Host"] = "non-local-host.com"
        #req.allow_redirects = False
        #s = requests.Session()
        #r = s.send(req.prepare())
        #self.assertTrue(r.is_redirect)
        #self.assertIn(FINAL_302_PAGE_SUFFIX, r.headers["Location"])


class ConnectBoxAPITestCase(unittest.TestCase):

    ADMIN_SSID_URL = "%s/api.php/ssid" % (getAdminBaseURL(),)
    ADMIN_HOSTNAME_URL = "%s/api.php/hostname" % (getAdminBaseURL(),)
    SUCCESS_RESPONSE = ["SUCCESS"]
    BAD_REQUEST_TEXT = "BAD REQUEST"

    @classmethod
    def setUpClass(cls):
        r = requests.get(cls.ADMIN_SSID_URL, auth=getAdminAuth())
        r.raise_for_status()
        cls._original_ssid = r.json()["result"][0]

    @classmethod
    def tearDownClass(cls):
        r = requests.put(cls.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": cls._original_ssid}))
        r.raise_for_status()

    def testAdminApiSmoketest(self):
        # To catch where there is a gross misconfiguration that breaks
        #  nginx/php
        r = requests.get(self.ADMIN_HOSTNAME_URL, auth=getAdminAuth())
        r.raise_for_status()
        self.assertEquals(r.json()["code"], 0)

    def testSSIDUnchRoundTrip(self):
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        initial_ssid = r.json()["result"][0]
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": initial_ssid}))
        r.raise_for_status()
        self.assertEquals(self.SUCCESS_RESPONSE, r.json()["result"])
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        r.raise_for_status()
        final_ssid = r.json()["result"][0]
        self.assertEquals(initial_ssid, final_ssid)

    def testSetSSID(self):
        new_ssid = "ssid-%s" % (random.randint(0, 1000000000),)
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": new_ssid}))
        r.raise_for_status()
        self.assertEquals(self.SUCCESS_RESPONSE, r.json()["result"])
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        self.assertEquals(new_ssid, r.json()["result"][0])

    def testBadRequestOnIncorrectRequestType(self):
        # Need to use PUT not POST
        r = requests.post(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                          data=json.dumps({"value": "some_ssid"}))
        with self.assertRaises(requests.HTTPError) as cm:
            r.raise_for_status()

        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(cm.exception.response.text, self.BAD_REQUEST_TEXT)

    def testBadRequestOnIncorrectDataType(self):
        # Need to use JSON encoded params
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data="value=some_ssid")
        with self.assertRaises(requests.HTTPError) as cm:
            r.raise_for_status()

        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(cm.exception.response.text, self.BAD_REQUEST_TEXT)

    def testBadRequestOnIncorrectFormVariable(self):
        # Need to use 'value' not 'ssid'
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"ssid": "some_ssid"}))
        with self.assertRaises(requests.HTTPError) as cm:
            r.raise_for_status()

        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(cm.exception.response.text, self.BAD_REQUEST_TEXT)

    def ssidSuccessfullySet(self, ssid_str):
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": ssid_str}))
        try:
            # This assumes there's not a better method to test whether
            #  the SSID was of a valid length...
            r.raise_for_status()
        except requests.HTTPError:
            return False

        if r.json()["result"] != self.SUCCESS_RESPONSE:
            return False

        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        r.raise_for_status()
        # Finally, check whether it was actually set
        return r.json()["result"][0] == ssid_str

    def _testSSIDSetWithLength(self, ssid_str):
        # SSIDs have a maximum length of 32 octets
        # http://standards.ieee.org/getieee802/download/802.11-2007.pdf
        valid_ssid_length = len(ssid_str.encode("utf-8")) <= 32
        self.assertEqual(valid_ssid_length, self.ssidSuccessfullySet(ssid_str))

    def test32CharacterPlainSSIDSet(self):
        self._testSSIDSetWithLength("a" * 32)

    def test32CharacterUnicodeSSIDSet(self):
        # ENG codepoint is a 2 byte character
        self._testSSIDSetWithLength(u'\N{LATIN SMALL LETTER ENG}' * 16)

    def test33CharacterPlainSSIDSet(self):
        # This SSID set should be rejected
        self._testSSIDSetWithLength("a" * 33)

    def test33CharacterUnicodeSSIDSet(self):
        # EM DASH codepoint is a 3 byte character
        # This SSID set should be rejected
        self._testSSIDSetWithLength(u'\N{EM DASH}' * 11)
