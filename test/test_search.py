from unittest import TestCase
import time
import json
import os
from search.search import ElasticSearchEngine


class SearchTest(TestCase):

    def setUp(self):
        self.search = ElasticSearchEngine("od-database-test")
        self.search.reset()
        time.sleep(0.5)

    def test_ping(self):
        self.assertTrue(self.search.ping(), "Search engine not running")

    def test_import_and_search(self):

        files = [
            {"name": "PaNopTicon", "size": 1000000000000000000, "path": "c/d", "mtime": 1528765672},
            {"name": "BLAckwAter.Park", "size": 123, "path": "", "mtime": None},
            {"name": "10'000 days", "size": -1, "path": "c", "mtime": 12345},
            {"name": "Dead Racer", "size": 1000, "path": "Speed Machine [FLAC]", "mtime": 12345}
        ]

        in_str = ""
        for file in files:
            in_str += json.dumps(file) + "\n"

        self.search.import_json(in_str, 123)
        time.sleep(2)
        self.assertEqual(4, self.search.es.count(self.search.index_name, "file")["count"])

        # Search for 'pan' in PaNopTicon and expect 1 result, a scroll id, and an highlight
        page = self.search.search("pan")
        self.assertIsNotNone(page["_scroll_id"])
        self.assertEqual(1, page["hits"]["total"])
        self.assertIsNotNone(page["hits"]["hits"][0]["highlight"]["name"])

        # Search for 'park' and expect BLAckwAter.Park
        page = self.search.search("park")
        self.assertEqual(1, page["hits"]["total"])

        # Search for fla and expect Dead Racer
        page = self.search.search("fla")
        self.assertEqual(1, page["hits"]["total"])

        # Search for 10'000 and expect 10'000 days
        page = self.search.search("10'000")
        self.assertEqual(1, page["hits"]["total"])

    def test_scroll(self):

        files = [
            {"name": "PaNopTicon", "size": 1000000000000000000, "path": "c/d", "mtime": 1528765672},
            {"name": "BLAckwAter.Park", "size": 123, "path": "", "mtime": None},
            {"name": "10'000 days", "size": -1, "path": "c", "mtime": 12345},
            {"name": "Dead Racer", "size": 1000, "path": "Speed Machine [FLAC]", "mtime": 12345}
        ]

        in_str = ""
        for file in files:
            in_str += json.dumps(file) + "\n"

        self.search.import_json(in_str, 123)
        time.sleep(2)

        page = self.search.search("")
        scroll_id = page["_scroll_id"]

        # next page
        next_page = self.search.scroll(scroll_id)
        next_scroll_id = next_page["_scroll_id"]
        self.assertIsNotNone(next_scroll_id)

        # again
        next_page2 = self.search.scroll(next_scroll_id)
        self.assertIsNotNone(next_page2["_scroll_id"])

    def test_invalid_scroll(self):

        invalid_scroll = "blahblah"

        self.assertIsNone(self.search.scroll(invalid_scroll))
