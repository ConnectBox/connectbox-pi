import functools
import json
import os
import time
import unittest
import random
import dns.resolver
import requests

TEST_IP_ENV_VAR = "TEST_IP"

# Default creds. Will need a way to override these when it changes
ADMIN_USER = "admin"
ADMIN_PASSWORD = "connectbox"
# Text in the welcome template
WELCOME_TEMPLATE_TEXT_SAMPLE = "<TITLE>Connected to ConnectBox Wifi</TITLE>"


def getTestTarget():
    try:
        return os.environ[TEST_IP_ENV_VAR]
    except KeyError:
        error_msg = "Set the %s environment variable" % \
            (TEST_IP_ENV_VAR,)
        raise RuntimeError(error_msg)


def getTestBaseURL():
    """Gets the ConnectBox base URL, solely from the IP address """

    # bounce through the 302, and retrieve the base connectbox page
    # We use the special "go" vhost as a host header, because this
    #  means we don't have to control DNS on the machine running
    #  these tests, and we don't need to expose a route in the CP
    #  flask App that gets us the base connectbox page
    r = requests.get(
        "http://%s/" % (getTestTarget(),),
        headers = {"Host": "go"},
        allow_redirects=False
    )
    r.raise_for_status()
    # and this is the ConnectBox base URL that we want
    return r.headers["Location"]


def getAdminBaseURL():
    return getTestBaseURL() + "/admin"


def getAdminAuth():
    return requests.auth.HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)


class ConnectBoxDNSTestCase(unittest.TestCase):
    """Behavioural tests for the dnsmasq server"""

    def setUp(self):
        """Simulate first connection

        Make sure the ConnectBox doesn't think the client has connected
        before, so we can test captive portal behaviour
        """
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [getTestTarget()]

    def testBasicDNSResponse(self):
        # Test the default response
        reply = self.resolver.query('google.com')

        # Expect an A record
        self.assertEqual(dns.rdatatype.to_text(reply.rdtype), 'A')

        # ... with a single item
        self.assertEqual(len(reply.rrset.items), 1)

        # ... containing the right address
        self.assertEqual(str(reply.rrset.items[0]), '10.129.0.1')

    def testAndroidDNSResponse(self):
        # Test the special host needed for Android Captive Portal
        reply = self.resolver.query('connectivitycheck.gstatic.com')

        # Expect an A record
        self.assertEqual(dns.rdatatype.to_text(reply.rdtype), 'A')

        # ... with a single item
        self.assertEqual(len(reply.rrset.items), 1)

        # ... containing a non-private IP
        self.assertEqual(str(reply.rrset.items[0]), '172.217.3.174')


class ConnectBoxCaptivePortalIntegration(unittest.TestCase):
    """
    Tests to demonstrate basic captive portal and connectbox integration
    """

    # Something that we will find in the CP welcome page
    CAPTIVE_PORTAL_SEARCH_TEXT = \
        "<TITLE>Connected to ConnectBox Wifi</TITLE>"

    def setUp(self):
        """Simulate first connection

        Make sure the ConnectBox doesn't think the client has connected
        before, so we can test captive portal behaviour
        """
        r = requests.delete("http://%s/_authorised_clients" %
                            (getTestTarget(),))
        r.raise_for_status()

    def tearDown(self):
        """Leave system in a clean state

        Make sure the ConnectBox won't think this client has connected
        before, regardless of whether the next connection is from a
        test, or from a normal browser or captive portal connection
        """
        r = requests.delete("http://%s/_authorised_clients" %
                            (getTestTarget(),))
        r.raise_for_status()

    def testAndroidEndpointSmokeTest(self):
        """Make sure it's there; nothing more complex"""
        r = requests.get("http://%s/generate_204" % (getTestTarget(),))
        r.raise_for_status()
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.CAPTIVE_PORTAL_SEARCH_TEXT, r.text)

    def testIOSEndpointSmokeTest(self):
        """Make sure it's there; nothing more complex"""
        r = requests.get("http://%s/hotspot-detect.html" % (getTestTarget(),))
        r.raise_for_status()
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.CAPTIVE_PORTAL_SEARCH_TEXT, r.text)


class ConnectBoxBasicTestCase(unittest.TestCase):
    def testContentResponseType(self):
        # URLs under content should return json
        r = requests.get("%s/content/" % (getTestBaseURL(),))
        r.raise_for_status()
        self.assertIsInstance(r.json(), list)

    def testTextInDocumentTitle(self):
        r = requests.get("%s/" % (getTestBaseURL(),))
        r.raise_for_status()
        self.assertIn("<title>ConnectBox</title>", r.text)


class ConnectBoxAPITestCase(unittest.TestCase):

    API_BASE_URL = "%s/api" % (getAdminBaseURL(),)
    ADMIN_SSID_URL = "%s/ssid" % API_BASE_URL
    ADMIN_HOSTNAME_URL = "%s/hostname" % API_BASE_URL
    ADMIN_STATICSITE_URL = "%s/staticsite" % API_BASE_URL
    ADMIN_SYSTEM_URL = "%s/system" % API_BASE_URL
    SUCCESS_RESPONSE = ["SUCCESS"]
    BAD_REQUEST_TEXT = "BAD REQUEST"

    @classmethod
    def setUpClass(cls):
        r = requests.get(cls.ADMIN_SSID_URL, auth=getAdminAuth())
        r.raise_for_status()
        cls._original_ssid = r.json()["result"][0]
        r = requests.get(cls.ADMIN_STATICSITE_URL, auth=getAdminAuth())
        r.raise_for_status()
        cls._original_staticsite = r.json()["result"][0]
        r = requests.get(cls.ADMIN_HOSTNAME_URL, auth=getAdminAuth())
        r.raise_for_status()
        cls._original_hostname = r.json()["result"][0]

    @classmethod
    def tearDownClass(cls):
        r = requests.put(cls.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": cls._original_ssid}))
        r.raise_for_status()
        r = requests.put(cls.ADMIN_STATICSITE_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": cls._original_staticsite}))
        r.raise_for_status()
        r = requests.put(cls.ADMIN_HOSTNAME_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": cls._original_hostname}))
        r.raise_for_status()

    def testAdminNeedsAuth(self):
        r = requests.get(self.API_BASE_URL)
        self.assertEqual(r.status_code, 401)
        r = requests.get(self.ADMIN_SSID_URL)
        self.assertEqual(r.status_code, 401)
        r = requests.get(self.ADMIN_HOSTNAME_URL)
        self.assertEqual(r.status_code, 401)
        r = requests.get(self.ADMIN_STATICSITE_URL)
        self.assertEqual(r.status_code, 401)

    def testAdminApiSmoketest(self):
        # To catch where there is a gross misconfiguration that breaks
        #  nginx/php
        r = requests.get(self.ADMIN_HOSTNAME_URL, auth=getAdminAuth())
        r.raise_for_status()
        self.assertEqual(r.json()["code"], 0)

    def testFactoryReset(self):
        r = requests.get(self.ADMIN_HOSTNAME_URL, auth=getAdminAuth())
        r.raise_for_status()
        hostname = r.json()["result"][0]

        expected_hostname = "resettest-%s" % (hostname,)
        r = requests.put(self.ADMIN_HOSTNAME_URL, auth=getAdminAuth(),
                     json={"value": expected_hostname})
        r.raise_for_status()

        # hostname has changed. Need to have admin hostname url point to
        #  new host until we've successfully reset
        # This will fail when retrieving the json if the hostname i.e.
        #  resettest-<originalhostname> can't be resolved by the machine
        #  running the tests. You'll have to add extra DNS entries if
        #  that happens
        newAdminHostnameURL = "%s/api/hostname" % (getAdminBaseURL(),)
        newSystemURL = "%s/api/system" % (getAdminBaseURL(),)
        r = requests.get(newAdminHostnameURL, auth=getAdminAuth())
        r.raise_for_status()
        updated_hostname = r.json()["result"][0]
        self.assertEqual(expected_hostname, updated_hostname)

        r = requests.post(newSystemURL, auth=getAdminAuth(),
                    json={"value": "reset"})
        r.raise_for_status()
        r = requests.get(self.ADMIN_HOSTNAME_URL, auth=getAdminAuth())
        r.raise_for_status()
        reset_hostname = r.json()["result"][0]
        self.assertEqual(hostname, reset_hostname)

    def testSSIDUnchRoundTrip(self):
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        initial_ssid = r.json()["result"][0]
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": initial_ssid}))
        r.raise_for_status()
        self.assertEqual(self.SUCCESS_RESPONSE, r.json()["result"])
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        r.raise_for_status()
        final_ssid = r.json()["result"][0]
        self.assertEqual(initial_ssid, final_ssid)

    def testSetSSID(self):
        new_ssid = "ssid-%s" % (random.randint(0, 1000000000),)
        r = requests.put(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                         data=json.dumps({"value": new_ssid}))
        r.raise_for_status()
        self.assertEqual(self.SUCCESS_RESPONSE, r.json()["result"])
        r = requests.get(self.ADMIN_SSID_URL, auth=getAdminAuth())
        self.assertEqual(new_ssid, r.json()["result"][0])

    def testBadRequestOnIncorrectRequestType(self):
        # Need to use PUT not POST
        r = requests.post(self.ADMIN_SSID_URL, auth=getAdminAuth(),
                          data=json.dumps({"value": "some_ssid"}))
        with self.assertRaises(requests.HTTPError) as cm:
            r.raise_for_status()

        self.assertEqual(cm.exception.response.status_code, 405)
        # The respons text is not that important and is framework dependent.
        #self.assertEqual(cm.exception.response.text, self.BAD_REQUEST_TEXT)

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

    def testStaticSiteSet(self):
        try:
            r = requests.put(self.ADMIN_STATICSITE_URL, auth=getAdminAuth(),
                             data=json.dumps({"value": "true"}))
            r.raise_for_status()
            self.assertEqual(r.json()["code"], 0)
            self.assertEqual(r.json()["result"], self.SUCCESS_RESPONSE)
        finally:
            r = requests.put(self.ADMIN_STATICSITE_URL, auth=getAdminAuth(),
                             data=json.dumps({"value": "false"}))
            r.raise_for_status()
            self.assertEqual(r.json()["code"], 0)
            self.assertEqual(r.json()["result"], self.SUCCESS_RESPONSE)

class ConnectBoxChatTestCase(unittest.TestCase):
    CHAT_MESSAGES_URL = "%s/chat/messages" % (getTestBaseURL())
    CHAT_TEXT_DIRECTION_URL = "%s/chat/messages/textDirection" % (getTestBaseURL())

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_get_messages(self):
        nick = "Foo"
        body = "message 1"
        text_direction = "ltr"
        req = requests.post(self.CHAT_MESSAGES_URL,
            json={"nick": nick, "body": body, "textDirection": text_direction})
        req.raise_for_status()

        response = req.json()
        self.assertTrue('result' in response)
        message = response['result']
        self.assertTrue('id' in message)
        id1 = message['id']

        body = "message 2"
        req = requests.post(self.CHAT_MESSAGES_URL,
            json={"nick": nick, "body": body, "textDirection": text_direction})
        req.raise_for_status()

        response = req.json()
        self.assertTrue('result' in response)
        message = response['result']
        self.assertTrue('id' in message)
        id2 = message['id']

        req = requests.get(self.CHAT_MESSAGES_URL)
        response = req.json()

        self.assertTrue('result' in response)
        messages = response['result']
        ids = []
        for msg in messages:
            self.assertTrue('id' in msg)
            self.assertTrue('timestamp' in msg)
            self.assertTrue('nick' in msg)
            self.assertTrue('body' in msg)
            self.assertTrue('textDirection' in msg)
            ids.append(msg['id'])

        self.assertTrue(id1 in ids)
        self.assertTrue(id2 in ids)

        req = requests.get('%s?max_id=%d' % (self.CHAT_MESSAGES_URL, (id2 - 1)))
        response = req.json()

        self.assertTrue('result' in response)
        messages = response['result']
        ids = []
        for msg in messages:
            self.assertTrue('id' in msg)
            self.assertTrue('timestamp' in msg)
            self.assertTrue('nick' in msg)
            self.assertTrue('body' in msg)
            self.assertTrue('textDirection' in msg)
            ids.append(msg['id'])

        self.assertFalse(id1 in ids)
        self.assertTrue(id2 in ids)

        req = requests.get('%s?max_id=%d' % (self.CHAT_MESSAGES_URL, id2))
        self.assertEqual(req.status_code, 204)

    def test_add_message(self):
        nick = "Foo"
        body = "message 1"
        text_direction = "ltr"
        req = requests.post(self.CHAT_MESSAGES_URL,
            json={"nick": nick, "body": body, "textDirection": text_direction})
        req.raise_for_status()

        response = req.json()
        self.assertTrue('result' in response)
        message = response['result']
        self.assertTrue('id' in message)

        id1 = message['id']

        body = "message 2"
        req = requests.post(self.CHAT_MESSAGES_URL,
            json={"nick": nick, "body": body, "textDirection": text_direction})
        req.raise_for_status()

        response = req.json()
        self.assertTrue('result' in response)
        message = response['result']
        self.assertTrue('id' in message)

        id2 = message['id']
        self.assertTrue(id2 > id1)

    def test_update_message(self):
        req = requests.put(self.CHAT_MESSAGES_URL,
            json={"nick": "Foo", "body": "message 1", "textDirection": "ltr"})

        self.assertEqual(req.status_code, 405)

    def test_expire_messages(self):
        req = requests.delete(self.CHAT_MESSAGES_URL)
        req.raise_for_status()

        response = req.json()
        self.assertTrue('result' in response)

        self.assertTrue(response['result'] >= 0)

    def text_default_text_direction(self):
        req = requests.get(self.CHAT_TEXT_DIRECTION_URL)
        req.raise_for_status()

        response = req.json()

        self.assertTrue('result' in response)
        self.assertTrue(response['result'] in ['ltr', 'rtl'])
