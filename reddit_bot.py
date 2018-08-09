import os
import time
import praw
import humanfriendly


class RedditBot:

    bottom_line = "^(Beep boop. I am a bot that calculates the file sizes & count of " \
                  "open directories posted in /r/opendirectories/)"

    def __init__(self, log_file: str, reddit: praw.Reddit):

        self.log_file = log_file

        self.crawled = []
        self.load_from_file()
        self.reddit = reddit

    def log_crawl(self, post_id):

        self.load_from_file()
        self.crawled.append(post_id)

        with open(self.log_file, "w") as f:
            for post_id in self.crawled:
                f.write(post_id + "\n")

    def has_crawled(self, post_id):
        self.load_from_file()
        return post_id in self.crawled

    def load_from_file(self):
        if not os.path.isfile(self.log_file):
            self.crawled = []
        else:
            with open(self.log_file, "r") as f:
                self.crawled = list(filter(None, f.read().split("\n")))

    def reply(self, reddit_obj, comment: str):

        while True:
            try:
                # Double check has_crawled
                if not self.has_crawled(reddit_obj.id):
                    reddit_obj.reply(comment)
                    self.log_crawl(reddit_obj.id)
                    print("Reply to " + reddit_obj.id)
                break
            except Exception as e:
                print("Waiting 5 minutes: " + str(e))
                time.sleep(300)
                continue

    @staticmethod
    def get_comment(stats: dict, website_id, message: str = ""):
        comment = message + "    \n" if message else ""

        comment += RedditBot.format_stats(stats)

        comment += "[Full Report](https://od-db.the-eye.eu/website/" + str(website_id) + "/)"
        comment += " | [Link list](https://od-db.the-eye.eu/website/" + str(website_id) + "/links)"
        comment += " | [Source](https://github.com/simon987/od-database)    \n"
        comment += "***    \n"
        comment += RedditBot.bottom_line

        return comment

    @staticmethod
    def format_stats(stats):

        result = "    \n"
        result += "File types | Count | Total Size\n"
        result += ":-- | :-- | :--    \n"
        counter = 0
        for mime in stats["ext_stats"]:
            result += mime[2]
            result += " | " + str(mime[1])
            result += " | " + humanfriendly.format_size(mime[0]) + "    \n"

            counter += 1
            if counter >= 3:
                break

        result += "**Total** | **" + str(stats["total_count"]) + "** | **"
        result += humanfriendly.format_size(stats["total_size"]) + "**    \n\n"
        return result
