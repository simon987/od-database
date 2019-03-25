import json
import logging
import os
import time
from threading import Thread
from uuid import uuid4

import urllib3

import config
import database
from search.search import ElasticSearchEngine
from task_tracker_drone.src.tt_drone.api import TaskTrackerApi, Worker
from ws_bucket_client.api import WsBucketApi

urllib3.disable_warnings()

logger = logging.getLogger("default")


class Task:

    def __init__(self, website_id: int, url: str, priority: int = 1,
                 callback_type: str = None, callback_args: str = None,
                 upload_token: str = None):
        self.website_id = website_id
        self.url = url
        self.priority = priority
        self.callback_type = callback_type
        self.callback_args = json.loads(callback_args) if callback_args else {}
        self.upload_token = upload_token

    def to_json(self):
        return {
            "website_id": self.website_id,
            "url": self.url,
            "callback_type": self.callback_type,
            "callback_args": json.dumps(self.callback_args),
            "upload_token": self.upload_token
        }

    def __str__(self):
        return json.dumps(self.to_json())

    def __repr__(self):
        return self.__str__()


class IndexingTask:

    def __init__(self, website_id: int, file_path: str, callback_type: str, callback_args):
        self.website_id = website_id
        self.file_path = file_path
        self.callback_type = callback_type
        self.callback_args = callback_args


class TaskManager:

    def __init__(self):
        self.search = ElasticSearchEngine("od-database")
        self.db = database.Database("db.sqlite3")
        self.tracker = TaskTrackerApi(config.TT_API)

        self.worker = Worker.from_file(self.tracker)
        if not self.worker:
            self.worker = self.tracker.make_worker("oddb_master")
            self.worker.dump_to_file()
            self.worker.request_access(config.TT_CRAWL_PROJECT, False, True)
            self.worker.request_access(config.TT_INDEX_PROJECT, True, False)

        self.bucket = WsBucketApi(config.WSB_API, config.WSB_SECRET)

        self._indexer_thread = Thread(target=self._do_indexing)
        self._indexer_thread.start()

    def _do_indexing(self):

        while True:
            logger.debug("Fetching indexing task...")
            task = self.tracker.fetch_task(worker=self.worker, project_id=config.TT_INDEX_PROJECT)

            if task:
                try:
                    recipe = task.json_recipe()
                    logger.debug("Got indexing task: " + str(recipe))
                    filename = os.path.join(config.WSB_PATH, format_file_name(recipe["website_id"], recipe["upload_token"]))
                except Exception as e:
                    print(e)
                finally:
                    try:
                        self._complete_task(filename, Task(recipe["website_id"], recipe["url"]))
                    except:
                        pass
            else:
                time.sleep(5)

    def _complete_task(self, file_list, task):

        self.search.delete_docs(task.website_id)

        if file_list:
            def iter_lines():
                with open(file_list, "r") as f:
                    line = f.readline()
                    while line:
                        yield line
                        line = f.readline()

            self.search.import_json(iter_lines(), task.website_id)

        self.db.update_website_date_if_exists(task.website_id)

    def fetch_indexing_task(self):

        task = self.tracker.fetch_task(worker=self.worker, project_id=config.TT_INDEX_PROJECT)
        print(task)

    def queue_task(self, task: Task):

        max_assign_time = 24 * 7 * 3600
        upload_token = uuid4().__str__()

        bucket_response = self.bucket.allocate(upload_token.__str__(),
                                               21474837499,  # 20Gib
                                               format_file_name(task.website_id, upload_token),
                                               to_dispose_date=int(time.time() + max_assign_time),
                                               upload_hook="")
        if not bucket_response:
            return

        print("Allocated upload bucket: %d, t=%s, r=%s" % (task.website_id, upload_token,  bucket_response.text))

        task.upload_token = upload_token
        tracker_response = self.worker.submit_task(config.TT_CRAWL_PROJECT,
                                                   recipe=task.__str__(),
                                                   priority=task.priority,
                                                   max_assign_time=max_assign_time,
                                                   hash64=task.website_id,
                                                   verification_count=1,
                                                   max_retries=3
                                                   )
        print("Queued task and made it available to crawlers: t=%s, r=%s" % (task, tracker_response.text))


def format_file_name(website_id, token):
    return "%d_%s.NDJSON" % (website_id, token, )

