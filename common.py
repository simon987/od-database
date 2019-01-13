from logging import FileHandler, StreamHandler

import sys

from database import Database
from search.search import ElasticSearchEngine
from tasks import TaskManager
import logging
from flask import session, abort

# Disable flask logging
flaskLogger = logging.getLogger('werkzeug')
flaskLogger.setLevel(logging.ERROR)

logger = logging.getLogger("default")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
file_handler = FileHandler("oddb.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(StreamHandler(sys.stdout))

taskManager = TaskManager()
searchEngine = ElasticSearchEngine("od-database")
searchEngine.start_stats_scheduler()
db = Database("db.sqlite3")


def require_role(role: str):

    if db.get_user_role(session.get("username", None)) != role:
        abort(403)
