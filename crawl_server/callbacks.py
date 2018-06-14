from crawl_server.database import Task
from crawl_server.reddit_bot import RedditBot
import praw


class PostCrawlCallback:

    def __init__(self, task: Task):
        self.task = task

    def run(self):
        raise NotImplementedError


class PostCrawlCallbackFactory:

    @staticmethod
    def get_callback(task: Task):

        if task.callback_type == "reddit_post":
            return RedditPostCallback(task)

        elif task.callback_type == "reddit_comment":
            return RedditCommentCallback(task)

        elif task.callback_type == "discord":
            return DiscordCallback(task)


class RedditCallback(PostCrawlCallback):

    def __init__(self, task: Task):
        super().__init__(task)

        reddit = praw.Reddit('opendirectories-bot',
                             user_agent='github.com/simon987/od-database (by /u/Hexahedr_n)')
        self.reddit_bot = RedditBot("crawled.txt", reddit)

    def run(self):
        raise NotImplementedError


class RedditPostCallback(RedditCallback):

    def run(self):
        print("Reddit post callback for task " + str(self.task))
        pass


class RedditCommentCallback(RedditCallback):

    def run(self):
        print("Reddit comment callback for task " + str(self.task))
        pass


class DiscordCallback(PostCrawlCallback):

    def run(self):
        print("Discord callback for task " + str(self.task))
        pass
