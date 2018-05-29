from unittest import TestCase
import sqlite3
from database import Database, File, Website, InvalidQueryException
import os


class DatabaseTest(TestCase):

    def tearDown(self):
        if os.path.exists("test.sqlite3"):
            os.remove("test.sqlite3")

    def test_init_database_existing(self):

        with open("test.sqlite3", "w"):
            pass

        Database("test.sqlite3")

        self.assertEqual(os.path.getsize("test.sqlite3"), 0)

    def test_init_database_new(self):

        Database("test.sqlite3")

        conn = sqlite3.connect("test.sqlite3")
        cur = conn.cursor()

        self.assertTrue(cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Website'"))

        conn.close()

    def test_insert_website(self):

        db = Database("test.sqlite3")
        website_id = db.insert_website(Website("https://google.ca", "127.0.0.1", "firefox"))

        conn = sqlite3.connect("test.sqlite3")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Website WHERE id=?", (website_id, ))

        db_website = cursor.fetchone()

        self.assertEqual(db_website[0], 1)
        self.assertEqual(db_website[1], "https://google.ca")
        self.assertEqual(db_website[2], "127.0.0.1")
        self.assertEqual(db_website[3], "firefox")
        self.assertIsNotNone(db_website[4])

    def test_insert_files(self):

        db = Database("test.sqlite3")
        website_id = db.insert_website(Website("", "", ""))
        db.insert_files([File(website_id, "/some/dir/", "text/plain", "file.txt", 1234)])

        conn = sqlite3.connect("test.sqlite3")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM File WHERE id=?", (1, ))
        db_file = cursor.fetchone()

        cursor.execute("SELECT * FROM WebsitePath WHERE id=?", (db_file[1], ))
        db_path = cursor.fetchone()

        self.assertEqual(db_file[0], 1)
        self.assertEqual(db_file[1], db_path[0])
        self.assertEqual(db_file[3], "file.txt")
        self.assertEqual(db_file[4], 1234)
        self.assertEqual(db_path[1], website_id)
        self.assertEqual(db_path[2], "/some/dir/")

    def test_import_json(self):

        db = Database("test.sqlite3")

        website_url = "http://google.ca/"
        logged_ip = "127.0.0.1"
        logged_useragent = "firefox"

        db.import_json("test/test_scan1.json", Website(website_url, logged_ip, logged_useragent))

        with sqlite3.connect("test.sqlite3") as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM File WHERE name='Bleach - Chapter 001.cbz'")
            db_file1 = cursor.fetchone()

            self.assertEqual(db_file1[4], 8770750)

            cursor.execute("SELECT * FROM File WHERE name='Bleach - Chapter 007.cbz'")
            db_file2 = cursor.fetchone()

            self.assertEqual(db_file2[4], 3443820)

    def test_select_website(self):

        db = Database("test.sqlite3")

        website_id = db.insert_website(Website("https://simon987.net/", "127.0.0.1", "firefox"))

        website = db.get_website_by_url("https://simon987.net/")

        self.assertEqual(website.url, "https://simon987.net/")
        self.assertEqual(website.logged_ip, "127.0.0.1")
        self.assertEqual(website.logged_useragent, "firefox")
        self.assertEqual(website.id, website_id)
        self.assertIsNotNone(website.last_modified)

        self.assertIsNone(db.get_website_by_url("does not exist"))

    def test_enqueue(self):

        db = Database("test.sqlite3")

        web_id = db.insert_website(Website("https://simon987.net", "127.0.0.1", "firefox"))

        db.enqueue(web_id)
        db.enqueue(web_id)

        with sqlite3.connect("test.sqlite3") as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM Queue")
            db_queued_website = cursor.fetchone()

            self.assertEqual(db_queued_website[0], 1)
            self.assertEqual(db_queued_website[1], web_id)
            self.assertIsNone(cursor.fetchone())

    def test_dequeue(self):

        db = Database("test.sqlite3")

        web_id_1 = db.insert_website(Website("", "", ""))
        web_id_2 = db.insert_website(Website("", "", ""))

        db.enqueue(web_id_1)
        db.enqueue(web_id_2, "postid")

        self.assertEqual(db.dequeue()[0], web_id_1)
        self.assertEqual(db.dequeue()[1], "postid")
        self.assertEqual(db.dequeue(), None)
        self.assertEqual(db.dequeue(), None)

    def test_queue(self):

        db = Database("test.sqlite3")

        db.enqueue(db.insert_website(Website("w1", "i1", "a1")))
        db.enqueue(db.insert_website(Website("w2", "i2", "a2")))
        db.enqueue(db.insert_website(Website("w3", "i3", "a3")))

        queue = db.queue()

        self.assertEqual(queue[0].url, "w1")
        self.assertEqual(queue[1].logged_ip, "i2")
        self.assertEqual(queue[2].logged_useragent, "a3")
        self.assertIsNotNone(queue[2].last_modified)
        self.assertEqual(len(queue), 3)

    def test_get_website_by_id(self):

        db = Database("test.sqlite3")

        website_id = db.insert_website(Website("a", "b", "c"))

        website = db.get_website_by_id(website_id)

        self.assertEqual(website.id, website_id)
        self.assertEqual(website.url, "a")
        self.assertEqual(website.logged_ip, "b")
        self.assertEqual(website.logged_useragent, "c")
        self.assertIsNone(db.get_website_by_id(999))

    def test_search_handle_invalid_query(self):

        db = Database("test.sqlite3")

        with self.assertRaises(InvalidQueryException):
            db.search(";DROP DATABASE;")
        with self.assertRaises(InvalidQueryException):
            db.search("invalidCol:")
        with self.assertRaises(InvalidQueryException):
            db.search("*test*")

    def test_stats(self):

        db = Database("test.sqlite3")

        db.get_stats()  # todo test