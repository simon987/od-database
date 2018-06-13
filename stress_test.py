import os
import json
import sys
from search.search import ElasticSearchEngine
from concurrent.futures import ThreadPoolExecutor
import requests
import random


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


def index_file_list(path: str, website_id):

    es = ElasticSearchEngine("od-database")
    with open(path, "r") as f:
        es.import_json(f.read(), website_id)


def search(term=""):
    requests.get("http://localhost/?&sort_order=score&per_page=100q=" + term, verify=False)
    print(term)


def random_searches(count=10000000, max_workers=1000):

    terms = requests.get("https://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain")\
        .text.splitlines()

    pool = ThreadPoolExecutor(max_workers=max_workers)
    pool.map(search, random.choices(terms, k=count))



# dump_local_filesystem("/mnt/")
# index_file_list("local_filesystem.json", 10)
# random_searches(100000)
