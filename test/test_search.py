from unittest import TestCase
import time
import json
import os
from search.search import ElasticSearchEngine


class SearchTest(TestCase):

    def setUp(self):
        self.search = ElasticSearchEngine("od-database-test")
        self.search.reset()
        time.sleep(1)

    def test_ping(self):
        self.assertTrue(self.search.ping(), "Search engine not running")

    def test_import_json(self):

        files = [
            {"name": "a", "size": 1000000000000000000, "path": "c/d", "mtime": 1528765672},
            {"name": "b", "size": 123, "path": "", "mtime": None},
            {"name": "c", "size": -1, "path": "c", "mtime": 12345}
        ]

        with open("tmp.json", "w") as f:
            for file in files:
                f.write(json.dumps(file) + "\n")

        self.search.import_json("tmp.json", 123)
        time.sleep(3)
        self.assertEqual(3, self.search.es.count(self.search.index_name, "file")["count"])

        os.remove("tmp.json")




