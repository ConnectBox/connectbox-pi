import os
import unittest
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

    def testAdminApiSmoketest(self):
        # To catch where there is a gross misconfiguration that breaks
        #  nginx/php
        r = requests.get("%s/api.php/hostname" % (ADMIN_BASE_URL,),
                         auth=getAdminAuth())
        self.assertEquals(r.json()["code"], 0)


class ConnectBoxWebDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.testTarget = getTestTarget()
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    def testPageTitle(self):
        self.browser.get(TEST_BASE_URL)
        self.assertIn("ConnectBox", self.browser.title)
