from unittest import TestCase
from od_util import is_valid_url


class InputValidationTest(TestCase):

    def test_valid_url(self):
        self.assertTrue(is_valid_url("https://google.ca/"))
        self.assertTrue(is_valid_url("http://google.ca/"))
        self.assertTrue(is_valid_url("http://www.google.ca/"))
        self.assertTrue(is_valid_url("http://www.subdomain.google.ca/"))
        self.assertTrue(is_valid_url("http://mộtsốkýtựngẫunhiên.whatever/"))
        self.assertTrue(is_valid_url("http://simon987.net:1234/"))
        self.assertTrue(is_valid_url("http://simon987.net:12345/"))

    def test_invalid_url(self):

        self.assertFalse(is_valid_url("ftp://simon987.net"))
        self.assertFalse(is_valid_url("git://simon987.net"))
        self.assertFalse(is_valid_url("simon987.net"))
        self.assertFalse(is_valid_url("http://simon987.net:8080"))
        self.assertFalse(is_valid_url("http://simon987/"))
