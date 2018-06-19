from search.search import ElasticSearchEngine
from database import Database
import csv
import os


def export(outfile="out.csv"):

    print("Export started, connecting to databases...")
    es = ElasticSearchEngine("od-database")
    db = Database("db.sqlite")
    docs = es.stream_all_docs()
    docs_with_website = db.join_website_on_scan(docs)

    print("Connected")

    with open(outfile + ".temp", "w") as out:

        csv_writer = csv.writer(out)
        csv_writer.writerow(["website_id", "website_url", "path", "name", "ext", "size", "mtime"])

        for doc in docs_with_website:
            csv_writer.writerow([doc["_source"]["website_id"],
                                 doc["_source"]["website_url"],
                                 doc["_source"]["path"] + "/" if doc["_source"]["path"] != "" else "",
                                 doc["_source"]["name"],
                                 "." + doc["_source"]["ext"] if doc["_source"]["ext"] != "" else "",
                                 doc["_source"]["size"],
                                 doc["_source"]["mtime"]])
    print("Wrote to csv, compressing with xz")

    os.system("xz " + outfile + ".temp")
    os.system("mv " + outfile + ".temp.xz " + outfile + ".xz")
    print("Compressed to " + str(os.path.getsize(outfile + ".xz")) + " bytes")


export("static/export.csv")
