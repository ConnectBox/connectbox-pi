import os
import unittest
from selenium import webdriver

TEST_IP_ENV_VAR = "TEST_IP"
TEST_BASE_URL = "http://biblebox.local"


class BibleBoxStaticTestCase(unittest.TestCase):

    def getTestTarget(self):
        try:
            return os.environ[TEST_IP_ENV_VAR]
        except KeyError:
            error_msg = "Set the %s environment variable" % \
                (TEST_IP_ENV_VAR,)
            raise RuntimeError(error_msg)

    def setUp(self):
        self.testTarget = self.getTestTarget()
        self.browser = webdriver.PhantomJS()
        self.addCleanup(self.browser.quit)

    def testPageTitle(self):
        self.browser.get(TEST_BASE_URL)
        self.assertIn("The BibleBox", self.browser.title)
