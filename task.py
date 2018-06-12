from apscheduler.schedulers.background import BackgroundScheduler
from crawl_server.database import Task, TaskResult
import requests
import json
from reddit_bot import RedditBot
import praw


class CrawlServer:

    headers = {
        "Content-Type": "application/json"
    }

    def __init__(self, url):
        self.url = url

    def queue_task(self, task: Task) -> bool:

        print("Sending task to crawl server " + self.url)
        payload = json.dumps(task.to_json())
        r = requests.post(self.url + "/task/put", headers=CrawlServer.headers, data=payload)
        print(r)
        return r.status_code == 200

    def get_completed_tasks(self) -> list:

        r = requests.get(self.url + "/task/completed")
        return [
            TaskResult(r["status_code"], r["file_count"], r["start_time"], r["end_time"], r["website_id"])
            for r in json.loads(r.text)]

    def get_queued_tasks(self) -> list:

        r = requests.get(self.url + "/task/")
        return [
            Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
            for t in json.loads(r.text)
        ]

    def get_current_tasks(self):

        r = requests.get(self.url + "/task/current")
        return [
            Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
            for t in json.loads(r.text)
        ]


class TaskDispatcher:

    def __init__(self):
        reddit = praw.Reddit('opendirectories-bot',
                             user_agent='github.com/simon987/od-database v1.0  (by /u/Hexahedr_n)')
        self.reddit_bot = RedditBot("crawled.txt", reddit)

        scheduler = BackgroundScheduler()
        scheduler.add_job(self.check_completed_tasks, "interval", seconds=1)
        scheduler.start()

        # TODO load from config
        self.crawl_servers = [
            CrawlServer("http://localhost:5001"),
        ]

    def check_completed_tasks(self):
        completed_tasks = []

        for server in self.crawl_servers:
            completed_tasks.extend(server.get_completed_tasks())

        if completed_tasks:
            print(str(len(completed_tasks)) + " completed tasks. Will index immediately")

    def dispatch_task(self, task: Task):
        self._get_available_crawl_server().queue_task(task)

    def _get_available_crawl_server(self) -> CrawlServer:
        # TODO: Load balancing & health check for crawl servers
        return self.crawl_servers[0]

    def get_queued_tasks(self) -> list:

        queued_tasks = []

        for server in self.crawl_servers:
            queued_tasks.extend(server.get_queued_tasks())

        return queued_tasks

    def get_current_tasks(self) -> list:

        current_tasks = []
        for server in self.crawl_servers:
            current_tasks.extend(server.get_current_tasks())

        return current_tasks


