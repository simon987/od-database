from crawl_server.database import TaskManagerDatabase, Task
from multiprocessing import Pool
from apscheduler.schedulers.background import BackgroundScheduler
from enum import Enum
from datetime import datetime
from crawler.crawler import RemoteDirectoryCrawler


class TaskResultStatus(Enum):
    SUCCESS = 0
    FAILURE = 1


class TaskResult:

    def __init__(self):
        self.status_code: TaskResultStatus = None
        self.file_count = 0
        self.start_time = None
        self.end_time = None
        self.website_id = None


class TaskManager:

    def __init__(self, db_path, max_processes=8):
        self.db = TaskManagerDatabase(db_path)
        self.pool = Pool(processes=max_processes)

        scheduler = BackgroundScheduler()
        scheduler.add_job(self.execute_queued_task, "interval", seconds=1)
        scheduler.start()

    def put_task(self, task: Task):
        self.db.put_task(task)

    def get_tasks(self):
        return self.db.get_tasks()

    def execute_queued_task(self):

        task = self.db.pop_task()
        if task:
            print("pooled " + task.url)
            self.pool.apply_async(
                TaskManager.run_task,
                args=(task, ),
                callback=TaskManager.task_complete
            )

    @staticmethod
    def run_task(task):
        result = TaskResult()
        result.start_time = datetime.utcnow()

        print("Starting task " + task.url)

        crawler = RemoteDirectoryCrawler(task.url, 10)
        crawler.crawl_directory()

        print("End task " + task.url)

        result.end_time = datetime.utcnow()

        return result

    @staticmethod
    def task_complete(result: TaskResult):
        print("Task done " + str(result))
        # todo save in db



