from crawl_server.database import TaskManagerDatabase, Task, TaskResult
from concurrent.futures import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from crawl_server.crawler import RemoteDirectoryCrawler


class TaskManager:

    def __init__(self, db_path, max_processes=8):
        self.db_path = db_path
        self.db = TaskManagerDatabase(db_path)
        self.pool = ProcessPoolExecutor(max_workers=max_processes)

        self.current_tasks = []

        scheduler = BackgroundScheduler()
        scheduler.add_job(self.execute_queued_task, "interval", seconds=5)
        scheduler.start()

    def put_task(self, task: Task):
        self.db.put_task(task)

    def get_tasks(self):
        return self.db.get_tasks()

    def get_current_tasks(self):
        return self.current_tasks

    def get_non_indexed_results(self):
        return self.db.get_non_indexed_results()

    def execute_queued_task(self):

        task = self.db.pop_task()
        if task:

            self.current_tasks.append(task)

            print("pooled " + task.url)

            self.pool.submit(
                TaskManager.run_task,
                task, self.db_path
            ).add_done_callback(TaskManager.task_complete)

    @staticmethod
    def run_task(task, db_path):
        result = TaskResult()
        result.start_time = datetime.utcnow()
        result.website_id = task.website_id

        print("Starting task " + task.url)

        crawler = RemoteDirectoryCrawler(task.url, 100)
        crawl_result = crawler.crawl_directory("./crawled/" + str(task.website_id) + ".json")

        result.file_count = crawl_result.file_count
        result.status_code = crawl_result.status_code

        result.end_time = datetime.utcnow()
        print("End task " + task.url)

        return result, db_path

    @staticmethod
    def task_complete(result):

        task_result, db_path = result.result()

        print(task_result.status_code)
        print(task_result.file_count)
        print(task_result.start_time)
        print(task_result.end_time)

        db = TaskManagerDatabase(db_path)
        db.log_result(task_result)
        print("Logged result to DB")

