from crawl_server.database import TaskManagerDatabase, Task, TaskResult
from multiprocessing import Pool
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from crawler.crawler import RemoteDirectoryCrawler


class TaskManager:

    def __init__(self, db_path, max_processes=8):
        self.db_path = db_path
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
                args=(task, self.db_path),
                callback=TaskManager.task_complete,
                error_callback=TaskManager.task_error
            )

    @staticmethod
    def run_task(task, db_path):
        result = TaskResult()
        result.start_time = datetime.utcnow()
        result.website_id = task.website_id

        print("Starting task " + task.url)

        crawler = RemoteDirectoryCrawler(task.url, 100)
        crawl_result = crawler.crawl_directory("crawled/" + str(task.website_id) + ".json")

        result.file_count = crawl_result.file_count
        result.status_code = crawl_result.status_code

        print("End task " + task.url)

        result.end_time = datetime.utcnow()

        return dict(result=result, db_path=db_path)

    @staticmethod
    def task_complete(kwargs):
        result = kwargs["result"]
        db_path = kwargs["db_path"]
        print(result.status_code)
        print(result.file_count)
        print(result.start_time)
        print(result.end_time)

        db = TaskManagerDatabase(db_path)
        db.log_result(result)

    @staticmethod
    def task_error(err):
        print("ERROR")
        print(err)



