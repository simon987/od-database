from apscheduler.schedulers.background import BackgroundScheduler
import os
from database import Website
from multiprocessing import Value, Process
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from database import Database
from reddit_bot import RedditBot
import praw


class TaskManager:

    def __init__(self):
        self.busy = Value("i", 0)
        self.current_website = None
        self.current_task = None

        reddit = praw.Reddit('opendirectories-bot',
                             user_agent='github.com/simon987/od-database v1.0  (by /u/Hexahedr_n)')
        self.reddit_bot = RedditBot("crawled.txt", reddit)

        self.db = Database("db.sqlite3")
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.check_new_task, "interval", seconds=1)
        scheduler.start()

    def check_new_task(self):
        if self.current_task is None:
            task = self.db.dequeue()

            if task:
                website_id, post_id = task
                website = self.db.get_website_by_id(website_id)
                self.current_task = Process(target=self.execute_task,
                                            args=(website, self.busy, post_id))
                self.current_website = website
                self.current_task.start()

        elif self.busy.value == 0:
            self.current_task.terminate()
            self.current_task = None
            self.current_website = None

    def execute_task(self, website: Website, busy: Value, post_id: str):
        busy.value = 1
        if os.path.exists("data.json"):
            os.remove("data.json")
        print("Started crawling task")
        process = CrawlerProcess(get_project_settings())
        process.crawl("od_links", base_url=website.url)
        process.start()
        print("Done crawling")

        self.db.import_json("data.json", website)
        os.remove("data.json")
        print("Imported in SQLite3")

        if post_id:
            stats = self.db.get_website_stats(website.id)
            comment = self.reddit_bot.get_comment(stats, website.id)
            print(comment)
            print(self.reddit_bot.reddit.submission(post_id))

        busy.value = 0
        print("Done crawling task")

