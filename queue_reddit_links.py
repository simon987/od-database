import praw
from crawl_server.reddit_bot import RedditBot
from search.search import ElasticSearchEngine
from database import Database, Website
import od_util
import os
import re

chars_to_remove_from_comment = re.compile("[\[\]\\\()]+")
reddit = praw.Reddit('opendirectories-bot',
                     user_agent='github.com/simon987/od-database v1.0  (by /u/Hexahedr_n)')
db = Database("db.sqlite3")
search = ElasticSearchEngine("od-database")
subreddit = reddit.subreddit("opendirectories")
# subreddit = reddit.subreddit("test")
bot = RedditBot("crawled.txt", reddit)

submissions = []


def handle_exact_repost(website_id, reddit_obj):
    stats = search.get_stats(website_id)
    comment = bot.get_comment({"": stats}, website_id,
                              "I already scanned this website on " + website.last_modified + " UTC")
    print(comment)
    print("Exact repost!")
    bot.reply(reddit_obj, comment)


def handle_subdir_repost(website_id, reddit_obj):

    website = db.get_website_by_id(website_id)
    message = "I already scanned a parent directory of this website on " + website.last_modified + " UTC"
    stats = db.get_website_stats(website_id)
    tables = {"Parent directory:": stats}

    subdir = url[len(website.url):]
    subdir_stats = db.get_subdir_stats(website_id, subdir)
    if subdir_stats["total_size"] <= 0:
        message += " but I couldn't calculate the size of this subdirectory."
    else:
        tables["Subdirectory `/" + subdir + "`:"] = subdir_stats
    comment = bot.get_comment(tables, website_id, message)
    print(comment)
    print("Subdir repost!")
    bot.reply(reddit_obj, comment)


# Check comments
for comment in subreddit.comments(limit=50):

    if not bot.has_crawled(comment):
        text = chars_to_remove_from_comment.sub(" ", comment.body).strip()
        if text.startswith("u/opendirectories-bot") or text.startswith("/u/opendirectories-bot"):
            lines = text.split()
            if len(lines) > 1:
                url = os.path.join(lines[1], "")  # Add trailing slash
                scanned = db.website_has_been_scanned(url)

                website = db.get_website_by_url(url)

                if website:
                    if not scanned:
                        # in progress
                        print(url)
                        print("In progress")
                        continue
                    handle_exact_repost(website.id, comment)
                    continue

                website_id = db.website_exists(url)
                if website_id:
                    if not scanned:
                        print("Parent in progress")
                        continue
                    handle_subdir_repost(website_id, comment)
                    continue

                if not od_util.is_valid_url(url):
                    print("Skipping reddit comment: Invalid url")
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you "
                                       "provided: `" + url + "` is not valid. Make sure that you include the"
                                       "'`http(s)://` prefix.    \n")
                    continue

                if od_util.is_blacklisted(url):
                    print("Skipping reddit comment: blacklisted")
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately my programmer has "
                                       "blacklisted this website. If you think that this is an error, please "
                                       "[contact him](https://old.reddit.com/message/compose?to=Hexahedr_n)")
                    continue

                if not od_util.is_od(url):
                    print("Skipping reddit comment: Not an OD")
                    print(url)
                    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you "
                                       "provided: `" + url + "` does not point to an open directory. This could also"
                                       " mean that the website is not responding (in which case, feel free to retry in "
                                       "a few minutes). If you think that this is an error, please "
                                       "[contact my programmer](https://old.reddit.com/message/compose?to=Hexahedr_n)")
                    continue

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
            scanned = db.website_has_been_scanned(url)

            website = db.get_website_by_url(url)

            if website:
                if not scanned:
                    print(url)
                    print("In progress")
                    continue
                handle_exact_repost(website.id, s)
                continue

            website_id = db.website_exists(url)
            if website_id:
                if not scanned:
                    print("Parent in progress")
                    continue
                handle_subdir_repost(website_id, s)
                continue

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

            web_id = db.insert_website(Website(url, "localhost", "reddit_bot"))
            db.enqueue(web_id, reddit_post_id=s.id, priority=3)  # Higher priority for reddit posts
            print("Queued reddit post: " + str(web_id))
