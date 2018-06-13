from flask import Flask, render_template, redirect, request, flash, abort, Response, send_from_directory, session
import json
import os
import time
import ssl
from database import Database, Website, InvalidQueryException
from flask_recaptcha import ReCaptcha
import od_util
import config
from flask_caching import Cache
from task import TaskDispatcher, Task
from search.search import ElasticSearchEngine

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

taskDispatcher = TaskDispatcher()
searchEngine = ElasticSearchEngine("od-database")


@app.template_filter("datetime_format")
def datetime_format(value, format='%Y-%m-%d'):
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
        stats = searchEngine.get_stats(website_id)
        stats["base_url"] = website.url
        stats["report_time"] = website.last_modified
        return json.dumps(stats)
    else:
        abort(404)


@app.route("/website/<int:website_id>/links")
def website_links(website_id):

    website = db.get_website_by_id(website_id)

    if website:
        print("FIXME: website_links")
        links = searchEngine.get_link_list(website_id, website.url)
        print(links)
        return Response("\n".join(links), mimetype="text/plain")
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

    if len(q) >= 3:
        try:
            hits = searchEngine.search(q, page, per_page, sort_order)
            hits = db.join_search_result(hits)
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

    stats = searchEngine.get_global_stats()
    stats["website_count"] = len(db.get_all_websites())
    current_websites = ", ".join(task.url for task in taskDispatcher.get_current_tasks())
    return render_template("home.html", stats=stats, current_websites=current_websites)


@app.route("/submit")
def submit():
    queued_websites = taskDispatcher.get_queued_tasks()
    return render_template("submit.html", queue=queued_websites, recaptcha=recaptcha)


def try_enqueue(url):

    url = os.path.join(url, "")
    website = db.get_website_by_url(url)

    if website:
        return "Website already exists", "danger"

    website = db.website_exists(url)
    if website:
        return "A parent directory of this url has already been posted", "danger"

    if not od_util.is_valid_url(url):
        return "<strong>Error:</strong> Invalid url. Make sure to include the appropriate scheme.", "danger"

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

    task = Task(web_id, url, priority=1)
    taskDispatcher.dispatch_task(task)

    return "The website has been added to the queue", "success"


@app.route("/enqueue", methods=["POST"])
def enqueue():
    # if recaptcha.verify():

        url = os.path.join(request.form.get("url"), "")
        message, msg_type = try_enqueue(url)
        flash(message, msg_type)

        return redirect("/submit")
    # else:
    #     flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
    #     return redirect("/submit")


@app.route("/enqueue_bulk", methods=["POST"])
def enqueue_bulk():
    # if recaptcha.verify():

        urls = request.form.get("urls")
        if urls:
            urls = urls.split()

            if 0 < len(urls) <= 10:

                for url in urls:
                    url = os.path.join(url, "")
                    message, msg_type = try_enqueue(url)
                    message += ' <span class="badge badge-' + msg_type + '">' + url + '</span>'
                    flash(message, msg_type)
                return redirect("/submit")

            else:
                flash("Too few or too many urls, please submit 1-10 urls", "danger")
                return redirect("/submit")
        else:
            return abort(500)

    # else:
    #     flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
    #     return redirect("/submit")


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


@app.route("/logout")
def admin_logout():
    session.clear()
    flash("Logged out", "info")
    return redirect("/")


@app.route("/dashboard")
def admin_dashboard():
    if "username" in session:

        tokens = db.get_tokens()

        return render_template("dashboard.html", api_tokens=tokens)
    else:
        return abort(403)


@app.route("/generate_token", methods=["POST"])
def admin_generate_token():
    if "username" in session:

        description = request.form.get("description")

        db.generate_api_token(description)
        flash("Generated API token", "success")

        return redirect("/dashboard")
    else:
        return abort(403)


@app.route("/del_token", methods=["POST"])
def admin_del_token():
    if "username" in session:

        token = request.form.get("token")

        db.delete_token(token)
        flash("Deleted API token", "success")
        return redirect("/dashboard")
    else:
        return abort(403)


if __name__ == '__main__':
    if config.USE_SSL:
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.load_cert_chain('certificates/cert.pem', 'certificates/privkey.pem')
        app.run("0.0.0.0", port=12345, ssl_context=context)
    else:
        app.run("0.0.0.0", port=12345)
