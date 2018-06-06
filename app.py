from flask import Flask, render_template, redirect, request, flash, abort, Response
import os
import json
from database import Database, Website, InvalidQueryException
from flask_recaptcha import ReCaptcha
import od_util
import sqlite3
from flask_caching import Cache
from task import TaskManager


app = Flask(__name__)
recaptcha = ReCaptcha(app=app,
                      site_key="6LfpFFsUAAAAADgxNJ9PIE9UVO3SM69MCxjzYyOM",
                      secret_key="6LfpFFsUAAAAADuzRvXZfq_nguS3RGj3FCA_2cc3")
app.secret_key = "A very secret key"
db = Database("db.sqlite3")
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.jinja_env.globals.update(truncate_path=od_util.truncate_path)
app.jinja_env.globals.update(get_color=od_util.get_color)
app.jinja_env.globals.update(get_mime=od_util.get_mime)

tm = TaskManager()


@app.route("/website/<int:website_id>/")
def website_info(website_id):

    website = db.get_website_by_id(website_id)

    if website:
        return render_template("website.html", website=website)
    else:
        abort(404)


@app.route("/website/<int:website_id>/json_chart")
@cache.memoize(30)
def website_json_chart(website_id):

    website = db.get_website_by_id(website_id)

    if website:
        stats = Response(json.dumps(db.get_website_stats(website_id)), mimetype="application/json")
        return stats
    else:
        abort(404)


@app.route("/website/<int:website_id>/links")
def website_links(website_id):

    website = db.get_website_by_id(website_id)

    if website:
        return Response("\n".join(db.get_website_links(website_id)), mimetype="text/plain")
    else:
        abort(404)


@app.route("/website/")
def websites():
    page = int(request.args.get("p")) if "p" in request.args else 0
    return render_template("websites.html", websites=db.get_websites(100, page))


@app.route("/search")
def search():

    q = request.args.get("q") if "q" in request.args else ""
    page = int(request.args.get("p")) if "p" in request.args else 0

    if q:
        try:
            hits = db.search(q, 100, page)
        except InvalidQueryException as e:
            flash("<strong>Invalid query:</strong> " + str(e), "warning")
            return redirect("/search")
    else:
        hits = None

    return render_template("search.html", results=hits, q=q, p=page)


@app.route("/contribute")
def contribute():
    return render_template("contribute.html")


@app.route("/")
def home():

    if tm.busy.value == 1:
        current_website = tm.current_website.url
    else:
        current_website = None

    try:
        stats = db.get_stats()
    except sqlite3.OperationalError:
        stats = None
    return render_template("home.html", stats=stats, current_website=current_website)


@app.route("/submit")
def submit():
    return render_template("submit.html", queue=db.queue(), recaptcha=recaptcha)


@app.route("/enqueue", methods=["POST"])
def enqueue():
    if not recaptcha.verify():

        url = os.path.join(request.form.get("url"), "")

        website = db.get_website_by_url(url)

        if website:
            flash("Website already exists", "danger")
            return redirect("/submit")

        website = db.website_exists(url)
        if website:
            flash("A parent directory of this url has already been posted", "danger")
            return redirect("/submit")

        if not od_util.is_valid_url(url):
            flash("<strong>Error:</strong> "
                  "Invalid url. Make sure to include the http(s):// suffix. "
                  "FTP is not supported", "danger")
            return redirect("/submit")

        if od_util.is_blacklisted(url):
            flash("<strong>Error:</strong> "
                  "Sorry, this website has been blacklisted. If you think "
                  "this is an error, please <a href='/contribute'>contact me</a>.", "danger")
            return redirect("/submit")

        if not od_util.is_od(url):
            flash("<strong>Error:</strong>"
                  "The anti-spam algorithm determined that the submitted url is not "
                  "an open directory or the server is not responding. If you think "
                  "this is an error, please <a href='/contribute'>contact me</a>.", "danger")

            return redirect("/submit")

        web_id = db.insert_website(Website(url, str(request.remote_addr), str(request.user_agent)))
        db.enqueue(web_id)
        flash("The website has been added to the queue", "success")

        return redirect("/submit")
    else:
        flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
        return redirect("/submit")


if __name__ == '__main__':
    app.run("0.0.0.0", port=12345)
