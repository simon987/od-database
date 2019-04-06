import json
import logging
import os
import time
from multiprocessing.pool import ThreadPool
from threading import Thread
from uuid import uuid4

import urllib3

import config
import database
from database import Website
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
        self.db = database.Database(config.DB_CONN_STR)
        self.tracker = TaskTrackerApi(config.TT_API)

        self.worker = Worker.from_file(self.tracker)
        if not self.worker:
            self.worker = self.tracker.make_worker("oddb_master")
            self.worker.dump_to_file()
            self.worker.request_access(config.TT_CRAWL_PROJECT, False, True)
            self.worker.request_access(config.TT_INDEX_PROJECT, True, False)

        self.bucket = WsBucketApi(config.WSB_API, config.WSB_SECRET)
        self._indexer_threads = list()

    def start_indexer_threads(self):
        logger.info("Starting %s indexer threads " % (config.INDEXER_THREADS, ))
        for _ in range(config.INDEXER_THREADS):
            t = Thread(target=self._do_indexing)
            t.setDaemon(True)
            self._indexer_threads.append(t)
            t.start()

    def _do_indexing(self):

        while True:
            task = self.worker.fetch_task(project_id=config.TT_INDEX_PROJECT)

            if task:
                try:
                    recipe = task.json_recipe()
                    logger.debug("Got indexing task: " + str(recipe))
                    filename = os.path.join(config.WSB_PATH,
                                            format_file_name(recipe["website_id"], recipe["upload_token"]))
                    self._complete_task(filename, Task(recipe["website_id"], recipe["url"]))
                except Exception as e:
                    self.worker.release_task(task_id=task.id, result=1, verification=0)
                finally:
                    try:
                        self.worker.release_task(task_id=task.id, result=0, verification=0)
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
            os.remove(file_list)

        self.db.update_website_date_if_exists(task.website_id)

    def do_recrawl(self):
        logger.debug("Creating re-crawl tasks")
        self._generate_crawling_tasks()

    def _generate_crawling_tasks(self):

        # TODO: Insert more in-depth re-crawl logic here
        websites_to_crawl = self.db.get_oldest_updated_websites(config.RECRAWL_POOL_SIZE, prefix="http")

        def recrawl(website: Website):
            crawl_task = Task(website.id, website.url,
                              priority=(int((time.time() - website.last_modified.timestamp()) / 3600)))
            self.queue_task(crawl_task)

        pool = ThreadPool(processes=30)
        pool.map(func=recrawl, iterable=websites_to_crawl)
        pool.close()

    def queue_task(self, task: Task):
        max_assign_time = 24 * 4 * 3600
        upload_token = uuid4().__str__()

        task.upload_token = upload_token
        tracker_response = self.worker.submit_task(config.TT_CRAWL_PROJECT,
                                                   recipe=task.__str__(),
                                                   priority=task.priority,
                                                   max_assign_time=max_assign_time,
                                                   hash64=task.website_id,
                                                   verification_count=1,
                                                   max_retries=3
                                                   )
        print(tracker_response.text)
        logging.info("Queued task and made it available to crawlers: t=%s, r=%s" % (task, tracker_response.text))
        if not tracker_response.json()["ok"]:
            return

        bucket_response = self.bucket.allocate(upload_token.__str__(),
                                               21474837499,  # 20Gib
                                               format_file_name(task.website_id, upload_token),
                                               to_dispose_date=int(time.time() + max_assign_time),
                                               upload_hook="")
        logging.info("Allocated upload bucket: %d, t=%s, r=%s" % (task.website_id, upload_token, bucket_response.text))


def format_file_name(website_id, token):
    return "%d_%s.NDJSON" % (website_id, token,)
