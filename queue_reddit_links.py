import praw
from reddit_bot import RedditBot
from database import Database, Website
import od_util
import os
import re

pattern = re.compile("[\[\]\\\()]+")
reddit = praw.Reddit('opendirectories-bot',
                     user_agent='github.com/simon987/od-database v1.0  (by /u/Hexahedr_n)')
db = Database("db.sqlite3")
# subreddit = reddit.subreddit("opendirectories")
subreddit = reddit.subreddit("test")
bot = RedditBot("crawled.txt", reddit)

submissions = []


def handle_exact_repost(website_id, reddit_obj):
    stats = db.get_website_stats(website_id)
    comment = bot.get_comment({"": stats}, website_id,
                              "I already scanned this website on " + website.last_modified + " UTC")
    print(comment)
    print("Exact repost!")
    bot.reply(reddit_obj, comment)


def handle_subdir_repost(website_id, reddit_obj):

    website = db.get_website_by_id(website_id)

    subdir = url[len(website.url):]

    subdir_stats = db.get_subdir_stats(website_id, subdir)
    stats = db.get_website_stats(website_id)
    comment = bot.get_comment({"Parent directory:": stats, "Subdirectory `/" + subdir + "`:": subdir_stats},
                              website_id, "I already scanned a parent directory of this website on"
                              + website.last_modified + " UTC")
    print(comment)
    print("Subdir repost!")
    bot.reply(reddit_obj, comment)


# Check comments
for comment in subreddit.comments(limit=50):

    if not bot.has_crawled(comment):
        text = pattern.sub(" ", comment.body).strip()
        if text.startswith("u/opendirectories-bot") or text.startswith("/u/opendirectories-bot"):
            lines = text.split()
            if len(lines) > 1:
                url = os.path.join(lines[1], "")  # Add trailing slash
                scanned = db.website_has_been_scanned(url)

                website = db.get_website_by_url(url)

                if website and not scanned:
                    # in progress
                    print("In progress")
                    continue

                if website and db.website_has_been_scanned(url):
                    bot.log_crawl(comment.id)
                    handle_exact_repost(website.id, comment)
                    continue

                website_id = db.website_exists(url)
                if website_id and not scanned:
                    # IN progress
                    print("Parent in progress")
                    continue
                if website_id and db.website_has_been_scanned(url):
                    bot.log_crawl(comment.id)
                    handle_subdir_repost(website_id, comment)
                    continue

                if not od_util.is_valid_url(url):
                    print("Skipping reddit comment: Invalid url")
                    bot.log_crawl(comment.id)
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you "
                                       "provided: `" + url + "` is not valid. Make sure that you include the"
                                       "'`http(s)://` prefix.    \n")
                    continue

                if od_util.is_blacklisted(url):
                    print("Skipping reddit comment: blacklisted")
                    bot.log_crawl(comment.id)
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately my programmer has "
                                       "blacklisted this website. If you think that this is an error, please "
                                       "[contact him](https://www.reddit.com/message/compose?to=Hexahedr_n)")
                    continue

                if not od_util.is_od(url):
                    print("Skipping reddit comment: Not an OD")
                    print(url)
                    bot.log_crawl(comment.id)
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you "
                                       "provided: `" + url + "` does not point to an open directory. This could also"
                                       " mean that the website is not responding (in which case, feel free to retry in "
                                       "a few minutes). If you think that this is an error, please "
                                       "[contact my programmer](https://www.reddit.com/message/compose?to=Hexahedr_n)")
                    continue

                bot.log_crawl(comment.id)
                web_id = db.insert_website(Website(url, "localhost", "reddit_bot"))
                db.enqueue(web_id, reddit_comment_id=comment.id, priority=2)  # Medium priority for reddit comments
                print("Queued comment post: " + str(web_id))


# Check posts
for submission in subreddit.new(limit=3):
    submissions.append(submission)


for s in submissions:

    if not s.is_self:
        if not bot.has_crawled(s.id):

            url = os.path.join(s.url, "")  # add trailing slash

            website = db.get_website_by_url(url)

            if website:
                bot.log_crawl(s.id)
                handle_exact_repost(website.id, s)

            website_id = db.website_exists(url)
            if website_id:
                bot.log_crawl(s.id)
                handle_subdir_repost(website_id, s)

            if not od_util.is_valid_url(url):
                print("Skipping reddit post: Invalid url")
                bot.log_crawl(s.id)
                continue

            if od_util.is_blacklisted(url):
                print("Skipping reddit post: blacklisted")
                bot.log_crawl(s.id)
                continue

            if not od_util.is_od(url):
                print("Skipping reddit post: Not an OD")
                print(url)
                bot.log_crawl(s.id)
                continue

            bot.log_crawl(s.id)
            web_id = db.insert_website(Website(url, "localhost", "reddit_bot"))
            db.enqueue(web_id, reddit_post_id=s.id, priority=3)  # Higher priority for reddit posts
            print("Queued reddit post: " + str(web_id))
