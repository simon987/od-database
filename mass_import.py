import fileinput
import os
from multiprocessing.pool import Pool

import od_util
from common import db, taskManager
from database import Website
from tasks import Task

urls = (line for line in fileinput.input())


def try_enqueue(url):
    url = os.path.join(url, "")
    url = od_util.get_top_directory(url)

    if not od_util.is_valid_url(url):
        return "<strong>Error:</strong> Invalid url. Make sure to include the appropriate scheme."

    website = db.get_website_by_url(url)
    if website:
        return "Website already exists"

    website = db.website_exists(url)
    if website:
        return "A parent directory of this url has already been posted"

    if db.is_blacklisted(url):
        return "<strong>Error:</strong> " \
               "Sorry, this website has been blacklisted. If you think " \
               "this is an error, please <a href='/contribute'>contact me</a>."

    if not od_util.is_od(url):
        return "<strong>Error:</strong>" \
               "The anti-spam algorithm determined that the submitted url is not " \
               "an open directory or the server is not responding. If you think " \
               "this is an error, please <a href='/contribute'>contact me</a>."

    website_id = db.insert_website(Website(url, "localhost", "mass_import.py"))

    task = Task(website_id, url, priority=2)
    taskManager.queue_task(task)

    return "The website has been added to the queue"


def check_url(url):
    url = os.path.join(url.strip(), "")
    try:
        print(try_enqueue(url))
    except:
        pass
    return None


pool = Pool(processes=50)
pool.map(func=check_url, iterable=urls)
pool.close()
