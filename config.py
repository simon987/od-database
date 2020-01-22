from os import environ

CAPTCHA_LOGIN = bool(environ.get("CAPTCHA_LOGIN", False))
CAPTCHA_SUBMIT = bool(environ.get("CAPTCHA_SUBMIT", False))
CAPTCHA_SEARCH = bool(environ.get("CAPTCHA_SEARCH", False))
CAPTCHA_EVERY = int(environ.get("CAPTCHA_EVERY", 10))

FLASK_SECRET = environ.get("FLASK_SECRET", "A very secret secret")
RESULTS_PER_PAGE = (12, 25, 50, 100, 250, 500, 1000)

SUBMIT_FTP = bool(environ.get("SUBMIT_FTP", False))
SUBMIT_HTTP = bool(environ.get("SUBMIT_HTTP", True))

TT_API = environ.get("TT_API", "http://localhost:3010")
TT_CRAWL_PROJECT = int(environ.get("TT_CRAWL_PROJECT", 3))
TT_INDEX_PROJECT = int(environ.get("TT_INDEX_PROJECT", 9))

WSB_API = environ.get("WSB_API", "http://localhost:3020")
WSB_SECRET = environ.get("WSB_API", "default_secret")

ES_URL = environ.get("ES_URL", "http://localhost:9200")
ES_INDEX = environ.get("ES_INDEX", "od-database")

REDIS_HOST = environ.get("REDIS_HOST", "localhost")
REDIS_PORT = environ.get("REDIS_PORT", 6379)

DB_CONN_STR = environ.get("DB_CONN_STR", "dbname=od_database user=od_database password=od_database")
RECRAWL_POOL_SIZE = environ.get("RECRAWL_POOL_SIZE", 10000)
INDEXER_THREADS = int(environ.get("INDEXER_THREAD", 3))
