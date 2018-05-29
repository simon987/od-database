import os
import time
import praw
import humanfriendly


class RedditBot:

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

    def reply(self, post_id: str, comment: str):

        submission = self.reddit.submission(id=post_id)

        while True:
            try:
                if not self.has_crawled(submission.id):
                    submission.reply(comment)
                    self.log_crawl(submission.id)
                break
            except Exception as e:
                print("Waiting 10 minutes: " + str(e))
                time.sleep(600)
                continue

    @staticmethod
    def get_comment(stats, website_id):

        comment = "File types | Count | Total Size\n"
        comment += ":-- | :-- | :--    \n"
        print(stats["mime_stats"])
        counter = 0
        for mime in stats["mime_stats"]:
            print(mime)
            comment += mime[2]
            comment += " | " + str(mime[1]) + "    \n"
            comment += " | " + str(mime[0]) + "    \n"

            counter += 1
            if counter >= 3:
                break

        comment += "**Total** | **" + str(stats["total_count"]) + "** | **"
        comment += humanfriendly.format_size(stats["total_size"]) + "**    \n\n"

        comment += "[Full Report](https://simon987.net/od-database/website/" + str(website_id) + "/)"
        comment += " | [Link list](https://simon987.net/od-database/website/" + str(website_id) + "/links)    \n"
        comment += "***    \n^(Beep boop. I am a bot that calculates the file sizes & count of"
        comment += " open directories posted in /r/opendirectories/)"

        return comment

