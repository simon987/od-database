from apscheduler.schedulers.background import BackgroundScheduler
from search.search import ElasticSearchEngine
from crawl_server.database import Task, TaskResult
import requests
from requests.exceptions import ConnectionError, ReadTimeout
import json
import database
from concurrent.futures import ThreadPoolExecutor
import urllib3

urllib3.disable_warnings()


class CrawlServer:

    def __init__(self, url, name, slots, token, server_id=None):
        self.url = url
        self.name = name
        self.slots = slots
        self.used_slots = 0
        self.token = token
        self.id = server_id

    def _generate_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": "Token " + self.token,
        }

    def queue_task(self, task: Task) -> bool:

        print("Sending task to crawl server " + self.url)
        try:
            payload = json.dumps(task.to_json())
            r = requests.post(self.url + "/task/put", headers=self._generate_headers(), data=payload, verify=False,
                              timeout=5)
            print(r)  # TODO: If the task could not be added, fallback to another server
            return r.status_code == 200
        except (ConnectionError, ReadTimeout):
            return False

    def pop_completed_tasks(self) -> list:

        try:
            r = requests.get(self.url + "/task/completed", headers=self._generate_headers(), verify=False, timeout=5)
            if r.status_code != 200:
                print("Problem while fetching completed tasks for '" + self.name + "': " + str(r.status_code))
                print(r.text)
                return []
            return [
                TaskResult(r["status_code"], r["file_count"], r["start_time"], r["end_time"], r["website_id"])
                for r in json.loads(r.text)]
        except (ConnectionError, ReadTimeout):
            print("Crawl server cannot be reached @ " + self.url)
            return []

    def fetch_queued_tasks(self):

        try:
            r = requests.get(self.url + "/task/", headers=self._generate_headers(), verify=False, timeout=5)

            if r.status_code != 200:
                print("Problem while fetching queued tasks for '" + self.name + "' " + str(r.status_code))
                print(r.text)
                return None

            return [
                Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
                for t in json.loads(r.text)
            ]
        except (ConnectionError, ReadTimeout):
            return None

    def fetch_current_tasks(self):

        try:
            r = requests.get(self.url + "/task/current", headers=self._generate_headers(), verify=False, timeout=5)

            if r.status_code != 200:
                print("Problem while fetching current tasks for '" + self.name + "' " + str(r.status_code))
                print(r.text)
                return None

            return [
                Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
                for t in json.loads(r.text)
            ]
        except (ConnectionError, ReadTimeout):
            return None

    def fetch_website_files(self, website_id) -> str:

        try:
            r = requests.get(self.url + "/file_list/" + str(website_id) + "/", stream=True,
                             headers=self._generate_headers(), verify=False)

            if r.status_code != 200:
                print("Problem while fetching website files for '" + self.name + "': " + str(r.status_code))
                print(r.text)
                return ""

            for line in r.iter_lines(chunk_size=1024 * 256):
                yield line
        except (ConnectionError, ReadTimeout):
            return ""

    def free_website_files(self, website_id) -> bool:

        try:
            r = requests.get(self.url + "/file_list/" + str(website_id) + "/free", headers=self._generate_headers(),
                             verify=False)
            return r.status_code == 200
        except (ConnectionError, ReadTimeout) as e:
            print(e)
            return False

    def pop_queued_tasks(self):
        try:
            r = requests.get(self.url + "/task/pop_all", headers=self._generate_headers(), verify=False)

            if r.status_code != 200:
                print("Problem while popping tasks for '" + self.name + "': " + str(r.status_code))
                print(r.text)

            return [
                Task(t["website_id"], t["url"], t["priority"], t["callback_type"], t["callback_args"])
                for t in json.loads(r.text)
            ]
        except (ConnectionError, ReadTimeout):
            return []


class TaskDispatcher:

    def __init__(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.check_completed_tasks, "interval", seconds=10)
        scheduler.start()

        self.search = ElasticSearchEngine("od-database")
        self.db = database.Database("db.sqlite3")

    def check_completed_tasks(self):

        for server in self.db.get_crawl_servers():
            for task in server.pop_completed_tasks():
                print("Completed task")

                task.server_id = server.id

                if task.file_count:
                    # All files are overwritten
                    self.search.delete_docs(task.website_id)
                    file_list = server.fetch_website_files(task.website_id)
                    self.search.import_json(file_list, task.website_id)
                    # File list is safe to delete once indexed
                    server.free_website_files(task.website_id)

                # Update last_modified date for website
                self.db.update_website_date_if_exists(task.website_id)

                self.db.log_result(task)

    def dispatch_task(self, task: Task):
        self._get_available_crawl_server().queue_task(task)

    def _get_available_crawl_server(self) -> CrawlServer:

        queued_tasks_by_server = self._get_queued_tasks_by_server()
        server_with_most_free_slots = None
        most_free_slots = -10000

        for server in queued_tasks_by_server:
            free_slots = server.slots - len(queued_tasks_by_server[server])
            if free_slots > most_free_slots:
                server_with_most_free_slots = server
                most_free_slots = free_slots

        print("Dispatching task to '" +
              server_with_most_free_slots.name + "' " +
              str(most_free_slots) + " free out of " + str(server_with_most_free_slots.slots))

        return server_with_most_free_slots

    def get_queued_tasks(self):

        queued_tasks_by_server = self._get_queued_tasks_by_server()
        for queued_tasks in queued_tasks_by_server.values():
            for task in queued_tasks:
                yield task

    def _get_queued_tasks_by_server(self) -> dict:

        queued_tasks = dict()
        pool = ThreadPoolExecutor(max_workers=10)
        crawl_servers = self.db.get_crawl_servers()
        responses = list(pool.map(lambda s: s.fetch_queued_tasks(), crawl_servers))
        pool.shutdown()

        for i, server in enumerate(crawl_servers):
            if responses[i] is not None:
                queued_tasks[server] = responses[i]

        return queued_tasks

    def get_current_tasks(self):

        current_tasks_by_server = self._get_current_tasks_by_server()
        for current_tasks in current_tasks_by_server.values():
            for task in current_tasks:
                yield task

    def _get_current_tasks_by_server(self) -> dict:

        current_tasks = dict()
        pool = ThreadPoolExecutor(max_workers=10)
        crawl_servers = self.db.get_crawl_servers()
        responses = list(pool.map(lambda s: s.fetch_current_tasks(), crawl_servers))
        pool.shutdown()

        for i, server in enumerate(crawl_servers):
            if responses[i] is not None:
                current_tasks[server] = responses[i]

        return current_tasks

    def redispatch_queued(self) -> int:

        counter = 0
        for server in self.db.get_crawl_servers():
            for task in server.pop_queued_tasks():
                self.dispatch_task(task)
                counter += 1

        return counter


