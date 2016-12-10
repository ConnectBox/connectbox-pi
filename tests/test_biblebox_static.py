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

    def setUp(self):
        self.testTarget = getTestTarget()
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    @unittest.skip("Base content page content being redefined")
    def testPageTitle(self):
        self.browser.get(TEST_BASE_URL)
        self.assertIn("The BibleBox", self.browser.title)

    def testBaseRedirect(self):
        r = requests.get("http://%s" % (self.testTarget,),
                         allow_redirects=False)
        self.assertTrue(r.is_redirect)
        self.assertEqual(r.headers["Location"], TEST_BASE_URL)
