import json
import os
import unittest
import random
import requests
from selenium import webdriver

TEST_IP_ENV_VAR = "TEST_IP"
TEST_BASE_URL = "http://connectbox.local"
ADMIN_BASE_URL = "http://connectbox.local/admin"
# Default creds. Will need a way to override these when it changes
ADMIN_USER = "admin"
ADMIN_PASSWORD = "connectbox"


def getTestTarget():
    try:
        return os.environ[TEST_IP_ENV_VAR]
    except KeyError:
        error_msg = "Set the %s environment variable" % \
            (TEST_IP_ENV_VAR,)
        raise RuntimeError(error_msg)


def getAdminAuth():
    return requests.auth.HTTPBasicAuth(ADMIN_USER, ADMIN_PASSWORD)


class ConnectBoxBasicTestCase(unittest.TestCase):

    def testBaseRedirect(self):
        r = requests.get("http://%s" % (getTestTarget(),),
                         allow_redirects=False)
        self.assertTrue(r.is_redirect)
        self.assertEqual(r.headers["Location"], TEST_BASE_URL)

    def testContentResponseType(self):
        # URLs under content should return json
        r = requests.get("%s/content/" % (TEST_BASE_URL,))
        self.assertIsInstance(r.json(), list)

    def testAdminNeedsAuth(self):
        r = requests.get("%s/" % (ADMIN_BASE_URL,))
        self.assertEquals(r.status_code, 401)

    def testAdminPageTitle(self):
        r = requests.get("%s/" % (ADMIN_BASE_URL,), auth=getAdminAuth())
        self.assertIn("ConnectBox Admin Dashboard", r.text)


class ConnectBoxAPITestCase(unittest.TestCase):

    ADMIN_SSID_URL = "%s/api.php/ssid" % (ADMIN_BASE_URL,)
    ADMIN_HOSTNAME_URL = "%s/api.php/hostname" % (ADMIN_BASE_URL,)
    SUCCESS_RESPONSE = ["SUCCESS"]
    BAD_REQUEST_TEXT = "BAD REQUEST"

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


class ConnectBoxWebDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.testTarget = getTestTarget()
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    def testPageTitle(self):
        self.browser.get(TEST_BASE_URL)
        self.assertIn("ConnectBox", self.browser.title)
