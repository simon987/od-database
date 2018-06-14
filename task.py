from apscheduler.schedulers.background import BackgroundScheduler
from search.search import ElasticSearchEngine
from crawl_server.database import Task, TaskResult
import requests
from requests.exceptions import ConnectionError
import json
import config


class CrawlServer:

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Token " + config.CRAWL_SERVER_TOKEN,
    }

    def __init__(self, url):
        self.url = url

    def queue_task(self, task: Task) -> bool:

        print("Sending task to crawl server " + self.url)
        try:
            payload = json.dumps(task.to_json())
            r = requests.post(self.url + "/task/put", headers=CrawlServer.headers, data=payload)
            print(r)
            return r.status_code == 200
        except ConnectionError:
            return False

    def fetch_completed_tasks(self) -> list:

        try:
            r = requests.get(self.url + "/task/completed", headers=CrawlServer.headers)
            return [
                TaskResult(r["status_code"], r["file_count"], r["start_time"], r["end_time"], r["website_id"])
                for r in json.loads(r.text)]
        except ConnectionError:
            print("Crawl server cannot be reached " + self.url)
            return []

    def fetch_queued_tasks(self) -> list:

        try:
            r = requests.get(self.url + "/task/", headers=CrawlServer.headers)
            return [
                Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
                for t in json.loads(r.text)
            ]
        except ConnectionError:
            return []

    def fetch_current_tasks(self):

        try:
            r = requests.get(self.url + "/task/current", headers=CrawlServer.headers)
            return [
                Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
                for t in json.loads(r.text)
            ]
        except ConnectionError:
            return []

    def fetch_website_files(self, website_id) -> str:

        try:
            r = requests.get(self.url + "/file_list/" + str(website_id) + "/", stream=True, headers=CrawlServer.headers)
            for line in r.iter_lines(chunk_size=1024 * 256):
                yield line
        except ConnectionError:
            return ""


class TaskDispatcher:

    def __init__(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.check_completed_tasks, "interval", seconds=10)
        scheduler.start()

        self.search = ElasticSearchEngine("od-database")

        # TODO load from config
        self.crawl_servers = [
            CrawlServer("http://localhost:5001"),
        ]

    def check_completed_tasks(self):

        for server in self.crawl_servers:
            for task in server.fetch_completed_tasks():
                print("Completed task")
                file_list = server.fetch_website_files(task.website_id)
                self.search.import_json(file_list, task.website_id)

    def dispatch_task(self, task: Task):
        self._get_available_crawl_server().queue_task(task)

    def _get_available_crawl_server(self) -> CrawlServer:
        # TODO: Load balancing & health check for crawl servers
        return self.crawl_servers[0]

    def get_queued_tasks(self) -> list:

        queued_tasks = []

        for server in self.crawl_servers:
            queued_tasks.extend(server.fetch_queued_tasks())

        return queued_tasks

    def get_current_tasks(self) -> list:
        # TODO mem cache this

        current_tasks = []
        for server in self.crawl_servers:
            current_tasks.extend(server.fetch_current_tasks())

        return current_tasks


