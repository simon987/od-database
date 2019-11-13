import os
import time

import lz4.frame

import config
from database import Database
from search.search import ElasticSearchEngine


def quote(string):
    if "\"" in string:
        return "\"" + string.replace("\"", "\"\"") + "\""
    elif "," in string:
        return "\"" + string + "\""
    else:
        return string


outfile = time.strftime("%Y-%m-%d_%H:%M:%S_dump.csv.lz4", time.gmtime())
dldir = "static/downloads/"

print("Deleting existing dumps")
for file in os.listdir(dldir):
    if file.endswith("_dump.csv.lz4"):
        os.remove(os.path.join(dldir, file))

print("Export started, connecting to databases...")

db = Database(config.DB_CONN_STR)
es = ElasticSearchEngine(config.ES_URL, config.ES_INDEX)

docs_with_url = db.join_website_url(es.stream_all_docs())

print("Connected, writing to csv")

with lz4.frame.open(outfile + ".part", mode='wb',
                    compression_level=9,
                    block_size=lz4.frame.BLOCKSIZE_MAX4MB) as fp:
    fp.write((",".join(
        ["website_id", "website_url", "path", "name", "ext", "size", "mtime"]
    ) + "\n").encode())

    for doc in docs_with_url:
        try:
            fp.write(
                (",".join(
                    [
                        str(doc["_source"]["website_id"]),
                        quote(doc["_source"]["website_url"]),
                        quote(doc["_source"]["path"]),
                        quote(doc["_source"]["name"]),
                        quote(doc["_source"]["ext"]),
                        str(doc["_source"]["size"]),
                        str(doc["_source"]["mtime"])
                    ]
                ) + "\n").encode())
        except Exception as e:
            print(e)
            print(doc)


os.rename(outfile + ".part", os.path.join(dldir, outfile))
