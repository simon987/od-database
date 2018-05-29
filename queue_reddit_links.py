import praw
from reddit_bot import RedditBot
from database import Database, Website
import od_util
from urllib.parse import urljoin

reddit = praw.Reddit('opendirectories-bot',
                     user_agent='github.com/simon987/od-database v1.0  (by /u/Hexahedr_n)')
db = Database("db.sqlite3")
subreddit = reddit.subreddit("opendirectories")

submissions = []

for submission in subreddit.new(limit=3):
    submissions.append(submission)

bot = RedditBot("crawled.txt", reddit)

for s in submissions:

    if not s.is_self:
        if not bot.has_crawled(s.id):

            url = urljoin(s.url, "")

            website = db.get_website_by_url(url)

            if website:
                continue

            website = db.website_exists(url)
            if website:
                print("Repost!")
                continue

            if not od_util.is_valid_url(url):
                print("Parent dir already posted!")
                continue

            if not od_util.is_od(url):
                print(url)
                continue

            web_id = db.insert_website(Website(url, "localhost", "reddit_bot"))
            db.enqueue(web_id, s.id, priority=2)  # Higher priority for reddit posts
            print("Queued " + str(web_id))
