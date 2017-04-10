import json
import os
import unittest
import random
import requests
from selenium import webdriver

TEST_IP_ENV_VAR = "TEST_IP"

# Default creds. Will need a way to override these when it changes
ADMIN_USER = "admin"
ADMIN_PASSWORD = "connectbox"
_testBaseURL = ""


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
        requests.get("http://%s/_forget_client" % (getTestTarget(),))
        # Register (no redirects given)
        r = requests.get("http://%s" % (getTestTarget(),),)
        # bounce through the 302, and retrieve the base connectbox page
        r = requests.get("http://%s" % (getTestTarget(),),)
        # and this is the ConnectBox base URL that we want
        _testBaseURL = r.url
        # Deregister the client, so that the test case that triggered
        #  this request starts with a clean slate
        requests.get("http://%s/_forget_client" % (getTestTarget(),))
    return _testBaseURL


def getAdminBaseURL():
    return getTestBaseURL() + "/admin"


def getAdminAuth():
    return requests.auth.HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)


class ConnectBoxBasicTestCase(unittest.TestCase):

    def testContentResponseType(self):
        # URLs under content should return json
        r = requests.get("%s/content/" % (getTestBaseURL(),))
        self.assertIsInstance(r.json(), list)

    def testAdminNeedsAuth(self):
        r = requests.get("%s/" % (getAdminBaseURL(),))
        self.assertEquals(r.status_code, 401)

    def testAdminNoTrailingSlashRequired(self):
        r = requests.get("%s" % (getAdminBaseURL(),), auth=getAdminAuth())
        self.assertIn("ConnectBox Admin Dashboard", r.text)

    def testAdminPageTitle(self):
        r = requests.get("%s/" % (getAdminBaseURL(),), auth=getAdminAuth())
        self.assertIn("ConnectBox Admin Dashboard", r.text)


class ConnectBoxDefaultVHostTestCase(unittest.TestCase):
    """Behavioural tests for the Nginx default vhost"""

    def setUp(self):
        """Simulate first connection

        Make sure the ConnectBox doesn't think the client has connected
        before, so we can test captive portal behaviour
        """
        requests.get("http://%s/_forget_client" % (getTestTarget(),))

    def tearDown(self):
        """Leave system in a clean state

        Make sure the ConnectBox won't think this client has connected
        before, regardless of whether the next connection is from a
        test, or from a normal browser or captive portal connection
        """
        requests.get("http://%s/_forget_client" % (getTestTarget(),))

    def testBaseRedirect(self):
        """Two hits on an unregistered route redirects to ConnectBox"""
        r = requests.get("http://%s" % (getTestTarget(),),)
        r = requests.get("http://%s" % (getTestTarget(),),
                         allow_redirects=False)
        self.assertTrue(r.is_redirect)
        self.assertIn("Location", r.headers)

    def testIOSCaptivePortalResponseForIOS(self):
        """Return the success.html page to bypass iOS captive portal login"""
        # Strictly this should be requesting an Apple page, but DNS.
        # See comments on testAndroidCaptivePortalResponse below
        headers = requests.utils.default_headers()
        # iOS and MacOS pre-Yosemite send something of this form
        headers.update({"User-Agent": "CaptiveNetworkSupport-346 wispr"})
        r = requests.get("http://%s/success.html" %
                         (getTestTarget(),), headers=headers)
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/success.html" %
                         (getTestTarget(),), headers=headers)
        self.assertIn("<BODY>\nSuccess\n</BODY>", r.text)

    def testYosemiteCaptivePortalResponseForYosemite(self):
        """Return the hotspot-detect.html page to bypass Yosemite login"""
        headers = requests.utils.default_headers()
        # MacOS Yosemite and later send something of this form
        headers.update({"User-Agent": "CaptiveNetworkSupport-346 wispr"})
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/hotspot-detect.html" %
                         (getTestTarget(),), headers=headers)
        #  us in the correct state
        self.assertIn("<BODY>\nSuccess\n</BODY>", r.text)

    def testAndroidCaptivePortalResponse(self):
        """Return a 204 status code to bypass Android captive portal login"""
        # Strictly this should be requesting
        #  http://clients3.google.com/generate_204 but answering requests for
        #  that site requires DNS mods, which can't be assumed for all
        #  people running these tests, so let's just poke for the page using
        #  the IP address of the server so we hit the default server, where
        #  this 204 redirection is active.
        r = requests.get("http://%s/generate_204" % (getTestTarget(),))
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/generate_204" % (getTestTarget(),))
        self.assertEquals(r.status_code, 204)

    def testAndroid7FallbackCaptivePortalResponse(self):
        """Return a 204 status code to bypass Android captive portal login"""
        # Strictly this should be requesting
        #  http://clients3.google.com/gen_204 but answering requests for
        #  that site requires DNS mods, which can't be assumed for all
        #  people running these tests, so let's just poke for the page using
        #  the IP address of the server so we hit the default server, where
        #  this 204 redirection is active.
        r = requests.get("http://%s/gen_204" % (getTestTarget(),))
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/gen_204" % (getTestTarget(),))
        self.assertEquals(r.status_code, 204)

    def testWindowsCaptivePortalResponse(self):
        """Return ncsi.txt to bypass windows captive portal login page"""
        r = requests.get("http://%s/ncsi.txt" % (getTestTarget(),))
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/ncsi.txt" % (getTestTarget(),))
        self.assertEquals("Microsoft NCSI", r.text)

    def testAmazonKindleCaptivePortalResponse(self):
        """Return wifistub.html to bypass kindle captive portal login page"""
        r = requests.get("http://%s/kindle-wifi/wifistub.html" %
                         (getTestTarget(),))
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/kindle-wifi/wifistub.html" %
                         (getTestTarget(),))
        self.assertIn("81ce4465-7167-4dcb-835b-dcc9e44c112a", r.text)

    def testFacebookMessengerConnectivityResponse(self):
        """Return 204 status code to bypass FB messenger connectivity check"""
        r = requests.get("http://%s/mobile/status.php" % (getTestTarget(),))
        # XXX - check a header to make sure the captive portal manager has
        #  us in the correct state
        r = requests.get("http://%s/mobile/status.php" % (getTestTarget(),))
        self.assertEquals(r.status_code, 204)


class ConnectBoxAPITestCase(unittest.TestCase):

    ADMIN_SSID_URL = "%s/api.php/ssid" % (getAdminBaseURL(),)
    ADMIN_HOSTNAME_URL = "%s/api.php/hostname" % (getAdminBaseURL(),)
    SUCCESS_RESPONSE = ["SUCCESS"]
    BAD_REQUEST_TEXT = "BAD REQUEST"

    @classmethod
    def setUpClass(cls):
        r = requests.get(cls.ADMIN_SSID_URL, auth=getAdminAuth())
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


class ConnectBoxWebDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    def testPageTitle(self):
        self.browser.get(getTestBaseURL())
        self.assertIn("ConnectBox", self.browser.title)
