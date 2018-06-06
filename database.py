import sqlite3
import datetime
import json
import os


class InvalidQueryException(Exception):
    pass


class Website:

    def __init__(self, url, logged_ip, logged_useragent, last_modified=None, website_id=None):
        self.url = url
        self.logged_ip = logged_ip
        self.logged_useragent = logged_useragent
        self.last_modified = last_modified
        self.id = website_id


class File:

    def __init__(self, website_id: int, path: str, mime: str, name: str, size: int):
        self.mime = mime
        self.size = size
        self.name = name
        self.path = path
        self.website_id = website_id


class Database:

    def __init__(self, db_path):

        self.db_path = db_path

        if not os.path.exists(db_path):
            self.init_database()

    def init_database(self):

        with open("init_script.sql", "r") as f:
            init_script = f.read()

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(init_script)
            conn.commit()

    def insert_website(self, website: Website):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Website (url, logged_ip, logged_useragent) VALUES (?,?,?)",
                           (website.url, website.logged_ip, website.logged_useragent))
            cursor.execute("SELECT LAST_INSERT_ROWID()")

            website_id = cursor.fetchone()[0]
            conn.commit()

        return website_id

    def insert_files(self, files: list):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert Paths first
            website_paths = dict()
            for file in files:
                if file.path not in website_paths:
                    cursor.execute("INSERT INTO WebsitePath (website_id, path) VALUES (?,?)",
                                   (file.website_id, file.path))
                    cursor.execute("SELECT LAST_INSERT_ROWID()")
                    website_paths[file.path] = cursor.fetchone()[0]

            # Then FileTypes
            mimetypes = dict()
            cursor.execute("SELECT * FROM FileType")
            db_mimetypes = cursor.fetchall()
            for db_mimetype in db_mimetypes:
                mimetypes[db_mimetype[1]] = db_mimetype[0]
            for file in files:
                if file.mime not in mimetypes:
                    cursor.execute("INSERT INTO FileType (mime) VALUES (?)", (file.mime, ))
                    cursor.execute("SELECT LAST_INSERT_ROWID()")
                    mimetypes[file.mime] = cursor.fetchone()[0]

            conn.commit()
            # Then insert files
            cursor.executemany("INSERT INTO File (path_id, name, size, mime_id) VALUES (?,?,?,?)",
                               [(website_paths[x.path], x.name, x.size, mimetypes[x.mime]) for x in files])

            # Update date
            if len(files) > 0:
                cursor.execute("UPDATE Website SET last_modified=CURRENT_TIMESTAMP WHERE id = ?",
                               (files[0].website_id, ))

            conn.commit()

    def import_json(self, json_file, website: Website):

        if not self.get_website_by_url(website.url):
            website_id = self.insert_website(website)
        else:
            website_id = website.id

        with open(json_file, "r") as f:
            try:
                self.insert_files([File(website_id, x["path"], os.path.splitext(x["name"])[1].lower(), x["name"], x["size"])
                                   for x in json.load(f)])
            except Exception as e:
                print(e)
                print("Couldn't read json file!")
                pass

    def get_website_by_url(self, url):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, url, logged_ip, logged_useragent, last_modified FROM Website WHERE url=?",
                           (url, ))
            db_web = cursor.fetchone()
        if db_web:
            website = Website(db_web[1], db_web[2], db_web[3], db_web[4], db_web[0])
            return website
        else:
            return None

    def get_website_by_id(self, website_id):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM Website WHERE id=?", (website_id, ))
            db_web = cursor.fetchone()

            if db_web:
                website = Website(db_web[1], db_web[2], db_web[3], db_web[4])
                website.id = db_web[0]
                return website
            else:
                return None

    def enqueue(self, website_id, reddit_post_id=None, reddit_comment_id=None, priority=1):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if reddit_post_id:
                cursor.execute("INSERT OR IGNORE INTO Queue (website_id, reddit_post_id, priority) VALUES (?,?,?)",
                               (website_id, reddit_post_id, priority))
            else:
                cursor.execute("INSERT OR IGNORE INTO Queue (website_id, reddit_comment_id, priority) VALUES (?,?,?)",
                               (website_id, reddit_comment_id, priority))
            conn.commit()

    def dequeue(self):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT website_id, reddit_post_id, reddit_comment_id"
                           " FROM Queue ORDER BY priority DESC, Queue.id ASC LIMIT 1")
            website = cursor.fetchone()

            if website:
                cursor.execute("DELETE FROM Queue WHERE website_id=?", (website[0],))
                return website[0], website[1], website[2]
            else:
                return None

    def queue(self):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT url, logged_ip, logged_useragent, last_modified "
                           "FROM Queue INNER JOIN Website ON website_id=Website.id "
                           "ORDER BY Queue.priority DESC, Queue.id ASC")

            return [Website(x[0], x[1], x[2], x[3]) for x in cursor.fetchall()]

    def get_stats(self):

        stats = {}
        with sqlite3.connect(self.db_path) as conn:

            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*), SUM(size) FROM File")
            db_files = cursor.fetchone()

            stats["file_count"] = db_files[0]
            stats["file_size"] = db_files[1]

            cursor.execute("SELECT COUNT(DISTINCT website_id), COUNT(id) FROM WebsitePath")
            db_websites = cursor.fetchone()
            stats["website_count"] = db_websites[0]
            stats["website_paths"] = db_websites[1]

            return stats

    def search(self, q, limit: int = 25, offset: int = 0):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT size, Website.url, WebsitePath.path, File.name, Website.id FROM File_index "
                               "INNER JOIN File ON File.id = File_index.rowid "
                               "INNER JOIN WebsitePath ON File.path_id = WebsitePath.id "
                               "INNER JOIN Website ON website_id = Website.id "
                               "WHERE File_index MATCH ? "
                               "ORDER BY rank LIMIT ? OFFSET ?", (q, limit, offset * limit))
            except sqlite3.OperationalError as e:
                raise InvalidQueryException(str(e))

            return cursor.fetchall()

    def get_website_stats(self, website_id):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT SUM(File.size), COUNT(*) FROM File "
                           "INNER JOIN WebsitePath Path on File.path_id = Path.id "
                           "WHERE Path.website_id = ?", (website_id, ))
            file_sum, file_count = cursor.fetchone()

            cursor.execute("SELECT SUM(File.size) as total_size, COUNT(File.id), FileType.mime FROM File "
                           "INNER JOIN FileType ON FileType.id = File.mime_id "
                           "INNER JOIN WebsitePath Path on File.path_id = Path.id "
                           "WHERE Path.website_id = ? "
                           "GROUP BY FileType.id ORDER BY total_size DESC", (website_id, ))
            db_mime_stats = cursor.fetchall()

            cursor.execute("SELECT Website.url, Website.last_modified FROM Website WHERE id = ?", (website_id, ))
            website_url, website_date = cursor.fetchone()

            return {
                "total_size": file_sum if file_sum else 0,
                "total_count": file_count if file_count else 0,
                "base_url": website_url,
                "report_time": website_date,
                "mime_stats": db_mime_stats
            }

    def get_subdir_stats(self, website_id: int, path: str):
        """Get stats of a sub directory. path must not start with / and must end with /"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT SUM(File.size), COUNT(*) FROM File "
                           "INNER JOIN WebsitePath Path on File.path_id = Path.id "
                           "WHERE Path.website_id = ? AND Path.path LIKE ?", (website_id, path + "%"))
            file_sum, file_count = cursor.fetchone()

            cursor.execute("SELECT SUM(File.size) as total_size, COUNT(File.id), FileType.mime FROM File "
                           "INNER JOIN FileType ON FileType.id = File.mime_id "
                           "INNER JOIN WebsitePath Path on File.path_id = Path.id "
                           "WHERE Path.website_id = ? AND Path.path LIKE ? "
                           "GROUP BY FileType.id ORDER BY total_size DESC", (website_id, path + "%"))
            db_mime_stats = cursor.fetchall()

            cursor.execute("SELECT Website.url, Website.last_modified FROM Website WHERE id = ?", (website_id, ))
            website_url, website_date = cursor.fetchone()

            return {
                "total_size": file_sum if file_sum else 0,
                "total_count": file_count if file_count else 0,
                "base_url": website_url,
                "report_time": website_date,
                "mime_stats": db_mime_stats
            }

    def get_website_links(self, website_id):
        """Get all download links of a website"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            website = self.get_website_by_id(website_id)

            cursor.execute("SELECT File.name, WebsitePath.path FROM File "
                           "INNER JOIN WebsitePath on File.path_id = WebsitePath.id "
                           "WHERE WebsitePath.website_id = ?", (website.id, ))

            return [website.url + x[1] + ("/" if len(x[1]) > 0 else "") + x[0] for x in cursor.fetchall()]

    def get_websites(self, per_page, page: int):
        """Get all websites"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT Website.id, Website.url, Website.last_modified FROM Website "
                           "ORDER BY last_modified DESC LIMIT ? OFFSET ?", (per_page, page * per_page))

            return cursor.fetchall()

    def website_exists(self, url):
        """Check if an url or the parent directory of an url already exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM Website WHERE url = substr(?, 0, length(url) + 1)", (url, ))
            website_id = cursor.fetchone()
            return website_id[0] if website_id else None

    def website_has_been_scanned(self, url):
        """Check if a website has at least 1 file"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            website_id = self.website_exists(url)

            if website_id:
                cursor.execute("SELECT COUNT(Path.id) FROM Website "
                               "INNER JOIN WebsitePath Path on Website.id = Path.website_id "
                               "WHERE Website.id = ?", (website_id, ))
                return cursor.fetchone()[0] > 0
        return None

    def clear_website(self, website_id):
        """Remove all files from a website and update its last_updated date"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM File WHERE File.path_id IN (SELECT WebsitePath.id "
                           "FROM WebsitePath WHERE WebsitePath.website_id=?)", (website_id, ))
            cursor.execute("DELETE FROM WebsitePath WHERE website_id=?", (website_id, ))
            cursor.execute("UPDATE Website SET last_modified=CURRENT_TIMESTAMP WHERE id=?", (website_id, ))
            conn.commit()

    def get_websites_older(self, delta: datetime.timedelta):
        """Get websites last updated before a given date"""
        date = datetime.datetime.utcnow() - delta

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Website.id FROM Website WHERE last_modified < ?", (date, ))
            return [x[0] for x in cursor.fetchall()]

    def get_websites_smaller(self, size: int):
        """Get the websites with total size smaller than specified"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Website.id FROM Website "
                           "INNER JOIN WebsitePath Path on Website.id = Path.website_id "
                           "INNER JOIN File F on Path.id = F.path_id "
                           "GROUP BY Website.id HAVING SUM(F.size) < ?", (size, ))
            return cursor.fetchall()

    def delete_website(self, website_id):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Website WHERE id=?", (website_id, ))
            conn.commit()
