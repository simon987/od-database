from flask import Flask, render_template, redirect, request, flash, abort, Response, send_from_directory, session
import os
import json
import time
import ssl
from database import Database, Website, InvalidQueryException
from flask_recaptcha import ReCaptcha
import od_util
import sqlite3
import config
from flask_caching import Cache
from task import TaskManager


app = Flask(__name__)
recaptcha = ReCaptcha(app=app,
                      site_key=config.CAPTCHA_SITE_KEY,
                      secret_key=config.CAPTCHA_SECRET_KEY)
app.secret_key = config.FLASK_SECRET
db = Database("db.sqlite3")
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.jinja_env.globals.update(truncate_path=od_util.truncate_path)
app.jinja_env.globals.update(get_color=od_util.get_color)
app.jinja_env.globals.update(get_mime=od_util.get_mime)

tm = TaskManager()


@app.template_filter("datetime_format")
def datetime_format(value, format='%Y-%m-%d %H:%M UTC'):
    return time.strftime(format, time.gmtime(value))


@app.route("/dl")
def downloads():

    try:
        export_file_stats = os.stat("static/out.csv.xz")
    except FileNotFoundError:
        print("No export file")
        export_file_stats = None

    return render_template("downloads.html", export_file_stats=export_file_stats)


@app.route("/get_export")
def get_export():

    if os.path.exists("static/out.csv.xz"):
        return send_from_directory("static", "out.csv.xz", as_attachment=True, mimetype="application/x-xz")
    return abort(404)


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
    sort_order = request.args.get("sort_order") if "sort_order" in request.args else "score"

    page = request.args.get("p") if "p" in request.args else "0"
    page = int(page) if page.isdigit() else 0

    per_page = request.args.get("per_page") if "per_page" in request.args else "50"
    per_page = int(per_page) if per_page.isdigit() else "50"
    per_page = per_page if per_page in config.RESULTS_PER_PAGE else 50

    if q:
        try:
            hits = db.search(q, per_page, page, sort_order)
        except InvalidQueryException as e:
            flash("<strong>Invalid query:</strong> " + str(e), "warning")
            return redirect("/search")
    else:
        hits = None

    return render_template("search.html",
                           results=hits, q=q, p=page, sort_order=sort_order,
                           per_page=per_page, results_set=config.RESULTS_PER_PAGE)


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


def try_enqueue(url):

    url = os.path.join(url, "")
    website = db.get_website_by_url(url)

    if website:
        return "Website already exists", "danger"

    website = db.website_exists(url)
    if website:
        return "A parent directory of this url has already been posted", "danger"

    if not od_util.is_valid_url(url):
        return "<strong>Error:</strong> Invalid url. Make sure to include the http(s):// suffix. " \
               "FTP is not supported", "danger"

    if od_util.is_blacklisted(url):

        return "<strong>Error:</strong> " \
              "Sorry, this website has been blacklisted. If you think " \
              "this is an error, please <a href='/contribute'>contact me</a>.", "danger"

    if not od_util.is_od(url):
        return "<strong>Error:</strong>" \
              "The anti-spam algorithm determined that the submitted url is not " \
              "an open directory or the server is not responding. If you think " \
              "this is an error, please <a href='/contribute'>contact me</a>.", "danger"

    web_id = db.insert_website(Website(url, str(request.remote_addr), str(request.user_agent)))
    db.enqueue(web_id)

    return "The website has been added to the queue", "success"


@app.route("/enqueue", methods=["POST"])
def enqueue():
    if recaptcha.verify():

        url = os.path.join(request.form.get("url"), "")
        message, msg_type = try_enqueue(url)
        flash(message, msg_type)

        return redirect("/submit")
    else:
        flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
        return redirect("/submit")


@app.route("/admin")
def admin_login_form():
    if "username" in session:
        return redirect("/dashboard")
    return render_template("admin.html", recaptcha=recaptcha)


@app.route("/login", methods=["POST"])
def admin_login():

    if recaptcha.verify():

        username = request.form.get("username")
        password = request.form.get("password")

        if db.check_login(username, password):
            session["username"] = username
            flash("Logged in", "success")
            return redirect("/dashboard")

        flash("Invalid username/password combo", "danger")
        return redirect("/admin")

    else:
        flash("Invalid captcha", "danger")
        return redirect("/admin")


@app.route("/dashboard")
def admin_dashboard():
    if "username" in session:
        return render_template("dashboard.html")
    else:
        return abort(403)


if __name__ == '__main__':
    if config.USE_SSL:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain('certificates/cert.pem', 'certificates/privkey.pem')
        app.run("0.0.0.0", port=12345, ssl_context=context)
    else:
        app.run("0.0.0.0", port=12345)
