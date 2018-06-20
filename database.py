import sqlite3
import datetime
import json
import os
import bcrypt
import uuid


class InvalidQueryException(Exception):
    pass


class Website:

    def __init__(self, url, logged_ip, logged_useragent, last_modified=None, website_id=None):
        self.url = url
        self.logged_ip = logged_ip
        self.logged_useragent = logged_useragent
        self.last_modified = last_modified
        self.id = website_id


class ApiToken:

    def __init__(self, token, description):
        self.token = token
        self.description = description


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

    def update_website_date_if_exists(self, website_id):

        with sqlite3.connect(self.db_path) as conn:

            cursor = conn.cursor()
            cursor.execute("UPDATE Website SET last_modified=CURRENT_TIMESTAMP WHERE id=?", (website_id, ))
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

    def get_websites_older(self, delta: datetime.timedelta):
        """Get websites last updated before a given date"""
        date = datetime.datetime.utcnow() - delta

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Website.id FROM Website WHERE last_modified < ?", (date, ))
            return [x[0] for x in cursor.fetchall()]

    def delete_website(self, website_id):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Website WHERE id=?", (website_id, ))
            conn.commit()

    def check_login(self, username, password) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT password FROM Admin WHERE username=?", (username, ))

            db_user = cursor.fetchone()

            if db_user:
                return bcrypt.checkpw(password.encode(), db_user[0])
            return False

    def generate_login(self, username, password) -> None:

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))

            cursor.execute("INSERT INTO Admin (username, password) VALUES (?,?)", (username, hashed_pw))
            conn.commit()

    def check_api_token(self, token) -> bool:

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT token FROM ApiToken WHERE token=?", (token, ))
            return cursor.fetchone() is not None

    def generate_api_token(self, description: str) -> str:

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            token = str(uuid.uuid4())
            cursor.execute("INSERT INTO ApiToken (token, description) VALUES (?, ?)", (token, description))
            conn.commit()

            return token

    def get_tokens(self) -> list:

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM ApiToken")

            return [ApiToken(x[0], x[1]) for x in cursor.fetchall()]

    def delete_token(self, token: str) -> None:

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM ApiToken WHERE token=?", (token, ))
            conn.commit()

    def get_all_websites(self) -> dict:

        # todo: mem cache that
        with sqlite3.connect(self.db_path) as conn:

            cursor = conn.cursor()

            cursor.execute("SELECT id, url FROM Website")

            result = {}

            for db_website in cursor.fetchall():
                result[db_website[0]] = db_website[1]
            return result

    def join_website_on_search_result(self, page: dict) -> dict:

        websites = self.get_all_websites()

        for hit in page["hits"]["hits"]:
            if hit["_source"]["website_id"] in websites:
                hit["_source"]["website_url"] = websites[hit["_source"]["website_id"]]
            else:
                hit["_source"]["website_url"] = "[DELETED]"

        return page

    def join_website_on_scan(self, docs: list):

        websites = self.get_all_websites()

        for doc in docs:
            if doc["_source"]["website_id"] in websites:
                doc["_source"]["website_url"] = websites[doc["_source"]["website_id"]]
            else:
                doc["_source"]["website_url"] = "[DELETED]"

            yield doc







