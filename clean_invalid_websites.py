from database import Database


db = Database("db.sqlite3")
websites_to_delete = db.get_websites_smaller(10000000)
for website_id in [x[0] for x in websites_to_delete]:
    db.clear_website(website_id)
    db.delete_website(website_id)
    print("Deleted " + str(website_id))