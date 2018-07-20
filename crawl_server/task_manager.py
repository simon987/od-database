from crawl_server import logger
import os
from tasks import TaskResult, Task
import config
import requests
import json
from multiprocessing import Manager, Pool
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from crawl_server.crawler import RemoteDirectoryCrawler


class TaskManager:

    def __init__(self, max_processes=2):
        self.pool = Pool(maxtasksperchild=1, processes=max_processes)
        self.max_processes = max_processes
        manager = Manager()
        self.current_tasks = manager.list()

        scheduler = BackgroundScheduler()
        scheduler.add_job(self.execute_queued_task, "interval", seconds=1)
        scheduler.start()

    def fetch_task(self):
        try:
            payload = {
                "token": config.API_TOKEN
            }
            r = requests.post(config.SERVER_URL + "/task/get", data=payload)

            if r.status_code == 200:
                text = r.text
                logger.info("Fetched task from server : " + text)
                task_json = json.loads(text)
                return Task(task_json["website_id"], task_json["url"])

            return None

        except Exception as e:
            raise e

    @staticmethod
    def push_result(task_result: TaskResult):

        try:

            logger.info("Uploading file list in small chunks")
            filename = "./crawled/" + str(task_result.website_id) + ".json"
            CHUNK_SIZE = 500000 * 10  # 5Mb
            if os.path.exists(filename):
                with open(filename) as f:
                    chunk = f.read(CHUNK_SIZE)
                    while chunk:
                        try:
                            payload = {
                                "token": config.API_TOKEN,
                                "website_id": task_result.website_id
                            }

                            files = {
                                "file_list": chunk
                            }

                            r = requests.post(config.SERVER_URL + "/task/upload", data=payload, files=files)
                            logger.info("RESPONSE: " + r.text)
                        except Exception as e:
                            logger.error("Exception while sending file_list chunk: " + str(e))
                            pass
                        chunk = f.read(CHUNK_SIZE)

            payload = {
                "token": config.API_TOKEN,
                "result": json.dumps(task_result.to_json())
            }

            r = requests.post(config.SERVER_URL + "/task/complete", data=payload)
            logger.info("RESPONSE: " + r.text)

            if os.path.exists(filename):
                os.remove(filename)

        except Exception as e:
            raise e

    def execute_queued_task(self):

        if len(self.current_tasks) <= self.max_processes:

            task = self.fetch_task()

            if task:
                logger.info("Submitted " + task.url + " to process pool")
                self.current_tasks.append(task)

                self.pool.apply_async(
                    TaskManager.run_task,
                    args=(task, self.current_tasks),
                    callback=TaskManager.task_complete,
                    error_callback=TaskManager.task_error
                )

    @staticmethod
    def run_task(task, current_tasks):

        result = TaskResult()
        result.start_time = datetime.utcnow().timestamp()
        result.website_id = task.website_id

        logger.info("Starting task " + task.url)

        crawler = RemoteDirectoryCrawler(task.url, config.CRAWL_SERVER_THREADS)
        crawl_result = crawler.crawl_directory("./crawled/" + str(task.website_id) + ".json")

        result.file_count = crawl_result.file_count
        result.status_code = crawl_result.status_code

        result.end_time = datetime.utcnow().timestamp()
        logger.info("End task " + task.url)

        return result, current_tasks

    @staticmethod
    def task_error(result):
        logger.error("Uncaught exception during a task: ")
        raise result

    @staticmethod
    def task_complete(result):

        task_result, current_tasks = result

        logger.info("Task completed, sending result to server")
        logger.info("Status code: " + task_result.status_code)
        logger.info("File count: " + str(task_result.file_count))

        TaskManager.push_result(task_result)

        for i, task in enumerate(current_tasks):
            if task.website_id == task_result.website_id:
                del current_tasks[i]


