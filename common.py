import logging
import sys
from logging import FileHandler, StreamHandler

import redis as r
from flask import session, abort

import config
from database import Database
from search.search import ElasticSearchEngine
from tasks import TaskManager

# Disable flask logging
flaskLogger = logging.getLogger('werkzeug')
flaskLogger.setLevel(logging.ERROR)

logger = logging.getLogger("default")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
file_handler = FileHandler("oddb.log")
file_handler.setFormatter(formatter)
for h in logger.handlers:
    logger.removeHandler(h)
logger.addHandler(file_handler)
logger.addHandler(StreamHandler(sys.stdout))

taskManager = TaskManager()
taskManager.start_indexer_threads()
searchEngine = ElasticSearchEngine("od-database")
searchEngine.start_stats_scheduler()
db = Database(config.DB_CONN_STR)

redis = r.Redis()


def require_role(role: str):

    if db.get_user_role(session.get("username", None)) != role:
        abort(403)
