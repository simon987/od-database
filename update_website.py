from database import Database
import od_util
import datetime


db = Database("db.sqlite3")

websites_to_update = db.get_websites_older(datetime.timedelta(minutes=5))

if websites_to_update:
    for website_id in websites_to_update:
        website = db.get_website_by_id(website_id)

        # Ignore if website is down
        if od_util.is_od(website.url):
            # If website is still up, re-scan it
            print("Re-scanning " + str(website_id))
            db.clear_website(website_id)
            db.enqueue(website_id)
        else:
            print("Website is down")
