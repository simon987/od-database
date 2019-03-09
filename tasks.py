import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from search.search import ElasticSearchEngine
import json
import database
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger("default")


class Task:

    def __init__(self, website_id: int, url: str, priority: int = 1,
                 callback_type: str = None, callback_args: str = None):
        self.website_id = website_id
        self.url = url
        self.priority = priority
        self.callback_type = callback_type
        self.callback_args = json.loads(callback_args) if callback_args else {}

    def to_json(self):
        return {
            "website_id": self.website_id,
            "url": self.url,
            "priority": self.priority,
            "callback_type": self.callback_type,
            "callback_args": json.dumps(self.callback_args)
        }

    def __str__(self):
        return json.dumps(self.to_json())

    def __repr__(self):
        return self.__str__()


class TaskResult:

    def __init__(self, status_code=None, file_count=0, start_time=0,
                 end_time=0, website_id=0, server_name=""):
        self.status_code = status_code
        self.file_count = file_count
        self.start_time = start_time
        self.end_time = end_time
        self.website_id = website_id
        self.server_name = server_name

    def to_json(self):
        return {
            "status_code": self.status_code,
            "file_count": self.file_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "website_id": self.website_id
        }


class TaskManager:

    def __init__(self):
        self.search = ElasticSearchEngine("od-database")
        self.db = database.Database("db.sqlite3")

    def complete_task(self, file_list, task, task_result, crawler_name):

        self.search.delete_docs(task_result.website_id)

        if file_list:
            def iter_lines():

                with open(file_list, "r") as f:
                    line = f.readline()
                    while line:
                        yield line
                        line = f.readline()

            self.search.import_json(iter_lines(), task.website_id)

        self.db.update_website_date_if_exists(task.website_id)

        task_result.server_id = crawler_name

        self.db.log_result(task_result)

    def queue_task(self, task: Task):
        self.db.put_task(task)
        print("Queued task and made it available to crawlers: " + str(task.website_id))

