from tasks import Task, TaskResult
from reddit_bot import RedditBot
import praw
from search.search import SearchEngine
import json


class PostCrawlCallback:

    def __init__(self, task: Task):
        self.task = task

        if self.task.callback_args:
            self.task.callback_args = json.loads(self.task.callback_args)

    def run(self, task_result: TaskResult, search: SearchEngine):
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

    def run(self, task_result: TaskResult, search: SearchEngine):
        raise NotImplementedError


class RedditPostCallback(RedditCallback):

    def run(self, task_result: TaskResult, search: SearchEngine):
        print("Reddit post callback for task " + str(self.task))


class RedditCommentCallback(RedditCallback):

    def run(self, task_result: TaskResult, search: SearchEngine):

        comment_id = self.task.callback_args["comment_id"]
        print("Editing comment comment " + comment_id)

        stats = search.get_stats(self.task.website_id)
        message = self.reddit_bot.get_comment(stats, self.task.website_id)
        print(message)
        self.reddit_bot.edit(self.reddit_bot.reddit.comment(comment_id), message)


class DiscordCallback(PostCrawlCallback):

    def run(self, task_result: TaskResult, search: SearchEngine):
        print("Discord callback for task " + str(self.task))
