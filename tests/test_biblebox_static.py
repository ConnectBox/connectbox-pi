import os
import unittest
import requests
from selenium import webdriver

TEST_IP_ENV_VAR = "TEST_IP"
TEST_BASE_URL = "http://biblebox.local"


def getTestTarget():
    try:
        return os.environ[TEST_IP_ENV_VAR]
    except KeyError:
        error_msg = "Set the %s environment variable" % \
            (TEST_IP_ENV_VAR,)
        raise RuntimeError(error_msg)


class BibleBoxStaticTestCase(unittest.TestCase):

    def testBaseRedirect(self):
        r = requests.get("http://%s" % (getTestTarget(),),
                         allow_redirects=False)
        self.assertTrue(r.is_redirect)
        self.assertEqual(r.headers["Location"], TEST_BASE_URL)

    def testAdminAuthPrompt(self):
        r = requests.get("%s/admin/" % (TEST_BASE_URL,),
                         allow_redirects=False)
        self.assertEquals(r.status_code, 401)

    def testContentResponseType(self):
        # Content should return json
        r = requests.get("%s/content/" % (TEST_BASE_URL,))
        self.assertIsInstance(r.json(), list)


class BibleBoxWebDriverTestCase(unittest.TestCase):

    def setUp(self):
        self.testTarget = getTestTarget()
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    def testPageTitle(self):
        self.browser.get(TEST_BASE_URL)
        self.assertIn("The BibleBox", self.browser.title)
