import time
import uuid
from urllib.parse import urlparse

import bcrypt
import psycopg2


class BlacklistedWebsite:
    def __init__(self, blacklist_id, url):
        self.id = blacklist_id
        self.netloc = url


class Website:

    def __init__(self, url, logged_ip, logged_useragent, last_modified=None, website_id=None):
        self.url = url
        self.logged_ip = logged_ip
        self.logged_useragent = logged_useragent
        self.last_modified = last_modified
        self.id = website_id


class ApiClient:

    def __init__(self, token, name):
        self.token = token
        self.name = name


class Database:

    def __init__(self, db_conn_str):
        self.db_conn_str = db_conn_str
        self.website_cache = dict()
        self.website_cache_time = 0

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_tables "
                           "WHERE tablename = 'searchlogentry')")

            if not cursor.fetchone()[0]:
                self.init_database()

    def init_database(self):

        print("Initializing database")

        with open("init_script.sql", "r") as f:
            init_script = f.read()

        with psycopg2.connect(self.db_conn_str) as conn:
            cur = conn.cursor()
            cur.execute(init_script)

    def update_website_date_if_exists(self, website_id):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Website SET last_modified=CURRENT_TIMESTAMP WHERE id=%s", (website_id,))
            conn.commit()

    def insert_website(self, website: Website):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Website (url, logged_ip, logged_useragent) VALUES (%s,%s,%s)",
                           (website.url, str(website.logged_ip), str(website.logged_useragent)))
            cursor.execute("SELECT LAST_INSERT_ROWID()")

            website_id = cursor.fetchone()[0]
            conn.commit()

        return website_id

    def get_website_by_url(self, url):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, url, logged_ip, logged_useragent, last_modified FROM Website WHERE url=%s",
                           (url,))
            db_web = cursor.fetchone()
        if db_web:
            website = Website(db_web[1], db_web[2], db_web[3], db_web[4], int(db_web[0].timestamp()))
            return website
        else:
            return None

    def get_website_by_id(self, website_id):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM Website WHERE id=%s", (website_id,))
            db_web = cursor.fetchone()

            if db_web:
                website = Website(db_web[1], db_web[2], db_web[3], int(db_web[4].timestamp()))
                website.id = db_web[0]
                return website
            else:
                return None

    def get_websites(self, per_page, page: int, url):
        """Get all websites"""
        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT Website.id, Website.url, Website.last_modified FROM Website "
                           "WHERE Website.url LIKE %s "
                           "ORDER BY last_modified DESC LIMIT %s OFFSET %s", (url + "%", per_page, page * per_page))

            return cursor.fetchall()

    def get_random_website_id(self):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM Website WHERE id >= (abs(random()) % (SELECT max(id) FROM Website)) LIMIT 1;")

            return cursor.fetchone()[0]

    def website_exists(self, url):
        """Check if an url or the parent directory of an url already exists"""
        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM Website WHERE url = substr(%s, 0, length(url) + 1)", (url,))
            website_id = cursor.fetchone()
            return website_id[0] if website_id else None

    def delete_website(self, website_id):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM Website WHERE id=%s", (website_id,))
            conn.commit()

    def check_login(self, username, password) -> bool:
        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT password FROM Admin WHERE username=%s", (username,))

            db_user = cursor.fetchone()

            if db_user:
                return bcrypt.checkpw(password.encode(), db_user[0].tobytes())
            return False

    def get_user_role(self, username: str):
        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT role FROM Admin WHERE username=%s", (username,))

            db_user = cursor.fetchone()

            if db_user:
                return db_user[0]
            return False

    def generate_login(self, username, password) -> None:

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))

            cursor.execute("INSERT INTO Admin (username, password, role) VALUES (%s,%s, 'admin')",
                           (username, hashed_pw))
            conn.commit()

    def check_api_token(self, token) -> str:

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM ApiClient WHERE token=%s", (token,))
            result = cursor.fetchone()
            return result[0] if result else None

    def generate_api_token(self, name: str) -> str:

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            token = str(uuid.uuid4())
            cursor.execute("INSERT INTO ApiClient (token, name) VALUES (%s, %s)", (token, name))
            conn.commit()

            return token

    def get_tokens(self) -> list:

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT token, name FROM ApiClient")

            return [ApiClient(x[0], x[1]) for x in cursor.fetchall()]

    def delete_token(self, token: str) -> None:

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM ApiClient WHERE token=%s", (token,))
            conn.commit()

    def get_all_websites(self) -> dict:
        if self.website_cache_time + 120 < time.time():
            with psycopg2.connect(self.db_conn_str) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id, url FROM Website")

                result = dict()

                for db_website in cursor.fetchall():
                    result[db_website[0]] = db_website[1]

                self.website_cache = result
                self.website_cache_time = time.time()

        return self.website_cache

    def join_website_on_search_result(self, page: dict) -> dict:

        websites = self.get_all_websites()

        for hit in page["hits"]["hits"]:
            if hit["_source"]["website_id"] in websites:
                hit["_source"]["website_url"] = websites[hit["_source"]["website_id"]]
            else:
                hit["_source"]["website_url"] = "[DELETED]"

        return page

    def join_website_url(self, docs):

        websites = self.get_all_websites()

        for doc in docs:
            if doc["_source"]["website_id"] in websites:
                doc["_source"]["website_url"] = websites[doc["_source"]["website_id"]]
            else:
                doc["_source"]["website_url"] = "[DELETED]"

            yield doc

    def join_website_on_stats(self, stats):

        websites = self.get_all_websites()

        for website in stats["website_scatter"]:
            website[0] = websites.get(website[0], "[DELETED]")

    def add_blacklist_website(self, url):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            parsed_url = urlparse(url)
            url = parsed_url.scheme + "://" + parsed_url.netloc
            cursor.execute("INSERT INTO BlacklistedWebsite (url) VALUES (%s)", (url,))
            conn.commit()

    def remove_blacklist_website(self, blacklist_id):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM BlacklistedWebsite WHERE id=%s", (blacklist_id,))
            conn.commit()

    def is_blacklisted(self, url):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()
            parsed_url = urlparse(url)
            url = parsed_url.scheme + "://" + parsed_url.netloc
            print(url)
            cursor.execute("SELECT id FROM BlacklistedWebsite WHERE url LIKE %s LIMIT 1", (url,))

            return cursor.fetchone() is not None

    def get_blacklist(self):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM BlacklistedWebsite")
            return [BlacklistedWebsite(r[0], r[1]) for r in cursor.fetchall()]

    def log_search(self, remote_addr, forwarded_for, q, exts, page, blocked, results, took):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO SearchLogEntry "
                "(remote_addr, forwarded_for, query, extensions, page, blocked, results, took) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (remote_addr, forwarded_for, q, ",".join(exts), page, blocked, results, took))

            conn.commit()

    def get_oldest_updated_websites(self, size: int):

        with psycopg2.connect(self.db_conn_str) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, url, last_modified FROM website "
                           "ORDER BY last_modified ASC LIMIT %s",
                           (size,))
            return [Website(url=r[1],
                            website_id=r[0],
                            last_modified=r[2],
                            logged_ip=None,
                            logged_useragent=None
                            )
                    for r in cursor.fetchall()]

