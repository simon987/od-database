import os
import json
import sys
from search.search import ElasticSearchEngine
from concurrent.futures import ThreadPoolExecutor
import requests
import random

terms = requests.get("https://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain") \
    .text.splitlines()
exts = [
    "zip", "exe", "mp3", "avi", "mp4", "rar", "7zip", "ogg", "m4a", "flac", "doc", "docx", "aac", "xls",
    "cab", "txt", "c", "java", "class", "jar", "py", "cpp", "h", "png", "jpg", "jpeg", "ttf", "torrent",
    "part", "blend", "3ds", "obj", "ico", "html", "css", "js", "ts", "ape", "asm", "nasm", "fasm", "o",
    "so", "dll", "tar", "gz", "bin", "cad", "cmd", "bat", "sh", "md"
]

def dump_local_filesystem(root_dir: str):

    docs = []

    for root, dirs, files in os.walk(root_dir):

        for filename in files:
            full_path = os.path.join(root, filename)
            stats = os.stat(full_path)

            doc = dict()
            doc["name"] = filename
            doc["path"] = root
            doc["mtime"] = stats.st_mtime
            doc["size"] = stats.st_size

            docs.append(doc)

    with open("local_filesystem.json", "w") as f:
            f.writelines(json.dumps(doc) + "\n" for doc in docs)


def random_path():
    return "/".join(random.choices(terms, k=random.randint(1, 5)))


def random_file_name():
    return random.choice(["_", " ", "-", ".", "#", ""]).\
               join(random.choices(terms, k=random.randint(1, 3))) + "." + random.choice(exts)


def get_random_file():

    doc = dict()
    doc["name"] = random_file_name()
    doc["path"] = random_path()
    doc["mtime"] = random.randint(0, 10000000)
    doc["size"] = random.randint(-1, 100000000000000)

    return doc


def dump_random_files(count=10):
    with open("random_dump.json", "w") as f:
        f.writelines(json.dumps(get_random_file()) + "\n" for _ in range(count))


def index_file_list(path: str, website_id):

    es = ElasticSearchEngine("od-database")
    with open(path, "r") as f:
        es.import_json(f.read(), website_id)


def search(term=""):
    requests.get("http://localhost/?&sort_order=score&per_page=100q=" + term, verify=False)
    print(term)


def random_searches(count=10000000, max_workers=1000):

    pool = ThreadPoolExecutor(max_workers=max_workers)
    pool.map(search, random.choices(terms, k=count))



# dump_local_filesystem("/mnt/")
# index_file_list("crawl_server/crawled/123.json", 10)
# random_searches(100000)
dump_random_files(20000 * 100000)
