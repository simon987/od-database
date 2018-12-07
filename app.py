from flask import Flask, render_template, redirect, request, flash, abort, Response, session
from multiprocessing import Pool
import json
from urllib.parse import urlparse
import logging
import os
import time
import datetime
from database import Database, Website
from flask_recaptcha import ReCaptcha
import od_util
import config
from flask_caching import Cache
from tasks import TaskManager, Task, TaskResult
from search.search import ElasticSearchEngine, InvalidQueryException
from callbacks import PostCrawlCallbackFactory
from threading import Lock

uploadLock = Lock()

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET

# Disable flask logging
flaskLogger = logging.getLogger('werkzeug')
flaskLogger.setLevel(logging.ERROR)

logger = logging.getLogger("default")

if config.CAPTCHA_SUBMIT or config.CAPTCHA_LOGIN:
    recaptcha = ReCaptcha(app=app,
                          site_key=config.CAPTCHA_SITE_KEY,
                          secret_key=config.CAPTCHA_SECRET_KEY)
else:
    recaptcha = None
if config.CAPTCHA_SEARCH:
    recaptcha_search = ReCaptcha(app=app,
                                 site_key=config.CAPTCHA_S_SITE_KEY,
                                 secret_key=config.CAPTCHA_S_SECRET_KEY)
else:
    recaptcha_search = None

db = Database("db.sqlite3")
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.jinja_env.globals.update(truncate_path=od_util.truncate_path)
app.jinja_env.globals.update(get_color=od_util.get_color)
app.jinja_env.globals.update(get_mime=od_util.get_category)

taskManager = TaskManager()
searchEngine = ElasticSearchEngine("od-database")
searchEngine.start_stats_scheduler()


@app.template_filter("date_format")
def date_format(value, format='%Y-%m-%d'):
    return time.strftime(format, time.gmtime(value))


@app.template_filter("datetime_format")
def datetime_format(value, format='%Y-%m-%d %H:%M:%S'):
    return time.strftime(format, time.gmtime(value))


@app.template_filter("duration_format")
def duration_format(value):
    delay = datetime.timedelta(seconds=value)
    if (delay.days > 0):
        out = str(delay).replace(" days, ", ":")
    else:
        out = str(delay)
    out_ar = out.split(':')
    out_ar = ["%02d" % (int(float(x))) for x in out_ar]
    out   = ":".join(out_ar)
    return out


@app.template_filter("from_timestamp")
def from_timestamp(value):
    return datetime.datetime.fromtimestamp(value)


@app.route("/dl")
@cache.cached(120)
def downloads():
    try:
        export_file_stats = os.stat("static/out.csv.lzm4")
    except FileNotFoundError:
        logger.warning("No export file to display in /dl")
        export_file_stats = None

    return render_template("downloads.html", export_file_stats=export_file_stats)


@app.route("/stats")
@cache.cached(120)
def stats_page():
    crawl_server_stats = db.get_stats_by_crawler()
    return render_template("stats.html", crawl_server_stats=crawl_server_stats)


@app.route("/stats/json_chart")
@cache.cached(240)
def stats_json():
    stats = searchEngine.get_global_stats()
    if stats:
        db.join_website_on_stats(stats)
        return Response(json.dumps(stats), mimetype="application/json")
    return abort(500)


@app.route("/website/<int:website_id>/")
def website_info(website_id):
    website = db.get_website_by_id(website_id)

    if website:
        return render_template("website.html", website=website)
    else:
        abort(404)


@app.route("/website/<int:website_id>/json_chart")
@cache.memoize(60)
def website_json_chart(website_id):
    website = db.get_website_by_id(website_id)

    if website:
        stats = searchEngine.get_stats(website_id)
        stats["base_url"] = website.url
        stats["report_time"] = website.last_modified
        return Response(json.dumps(stats), mimetype="application/json")
    else:
        abort(404)


@app.route("/website/<int:website_id>/links")
def website_links(website_id):
    website = db.get_website_by_id(website_id)

    if website:
        links = searchEngine.get_link_list(website_id, website.url)
        return Response("\n".join(links), mimetype="text/plain")
    else:
        abort(404)


@app.route("/website/")
def websites():
    page = int(request.args.get("p")) if "p" in request.args else 0
    url = request.args.get("url") if "url" in request.args else ""
    if url:
        parsed_url = urlparse(url)
        if parsed_url.scheme:
            search_term = (parsed_url.scheme + "://" + parsed_url.netloc)
        else:
            flash("Sorry, I was not able to parse this url format. "
                  "Make sure you include the appropriate scheme (http/https/ftp)", "warning")
            search_term = ""
    else:
        search_term = url

    return render_template("websites.html",
                           websites=db.get_websites(50, page, search_term),
                           p=page, url=search_term, per_page=50)


@app.route("/website/random")
def random_website():
    return redirect("/website/" + str(db.get_random_website_id()))


## TODO: move to DB
def get_empty_websites():
    current_tasks = taskManager.get_queued_tasks()

    queued_websites = [task.website_id for task in current_tasks]
    all_websites = db.get_all_websites()
    non_queued_websites = list(set(all_websites).difference(queued_websites))

    return searchEngine.are_empty(non_queued_websites)


@app.route("/website/delete_empty")
def admin_delete_empty_website():
    """Delete websites with no associated files that are not queued"""

    if "username" in session:

        empty_websites = get_empty_websites()

        for website in empty_websites:
            # db.delete_website(website)
            pass

        flash("Deleted: " + repr(list(empty_websites)), "success")
        return redirect("/dashboard")

    else:
        abort(403)


@app.route("/website/<int:website_id>/clear")
def admin_clear_website(website_id):
    if "username" in session:

        searchEngine.delete_docs(website_id)
        flash("Cleared all documents associated with this website", "success")
        return redirect("/website/" + str(website_id))
    else:
        abort(403)


@app.route("/website/<int:website_id>/delete")
def admin_delete_website(website_id):
    if "username" in session:

        searchEngine.delete_docs(website_id)
        db.delete_website(website_id)
        flash("Deleted website " + str(website_id), "success")
        return redirect("/website/")

    else:
        abort(403)


@app.route("/website/<int:website_id>/rescan")
def admin_rescan_website(website_id):
    if "username" in session:

        website = db.get_website_by_id(website_id)

        if website:
            priority = request.args.get("priority") if "priority" in request.args else 1
            task = Task(website_id, website.url, priority)
            taskManager.queue_task(task)

            flash("Enqueued rescan task", "success")
        else:
            flash("Website does not exist", "danger")
        return redirect("/website/" + str(website_id))

    else:
        abort(403)


@app.route("/search")
def search():
    q = request.args.get("q") if "q" in request.args else ""
    sort_order = request.args.get("sort_order") if "sort_order" in request.args else "score"

    page = request.args.get("p") if "p" in request.args else "0"
    page = int(page) if page.isdigit() else 0

    per_page = request.args.get("per_page") if "per_page" in request.args else "50"
    per_page = int(per_page) if per_page.isdigit() else "50"
    per_page = per_page if per_page in config.RESULTS_PER_PAGE else 50

    extensions = request.args.get("ext") if "ext" in request.args else None
    extensions = [ext.strip().strip(".").lower() for ext in extensions.split(",")] if extensions else []

    size_min = request.args.get("size_min") if "size_min" in request.args else "size_min"
    size_min = int(size_min) if size_min.isdigit() else 0
    size_max = request.args.get("size_max") if "size_max" in request.args else "size_max"
    size_max = int(size_max) if size_max.isdigit() else 0

    date_min = request.args.get("date_min") if "date_min" in request.args else "date_min"
    date_min = int(date_min) if date_min.isdigit() else 0
    date_max = request.args.get("date_max") if "date_max" in request.args else "date_max"
    date_max = int(date_max) if date_max.isdigit() else 0

    match_all = "all" in request.args

    field_name = "field_name" in request.args
    field_trigram = "field_trigram" in request.args
    field_path = "field_path" in request.args

    if not field_name and not field_trigram and not field_path:
        # If no fields are selected, search in all
        field_name = field_path = field_trigram = True

    fields = []
    if field_path:
        fields.append("path")
    if field_name:
        fields.append("name^5")
    if field_trigram:
        fields.append("name.nGram^2")

    if len(q) >= 3:

        blocked = False
        hits = None
        response = request.args.get("g-recaptcha-response", "")
        if not config.CAPTCHA_SEARCH or recaptcha_search.verify(response):

            try:
                hits = searchEngine.search(q, page, per_page, sort_order,
                                           extensions, size_min, size_max, match_all, fields, date_min, date_max)
                hits = db.join_website_on_search_result(hits)
            except InvalidQueryException as e:
                flash("<strong>Invalid query:</strong> " + str(e), "warning")
                blocked = True
            except:
                flash("Query failed, this could mean that the search server is overloaded or is not reachable. "
                      "Please try again later", "danger")

            results = hits["hits"]["total"] if hits else -1
            took = hits["took"] if hits else -1
            forwarded_for = request.headers["X-Forwarded-For"] if "X-Forwarded-For" in request.headers else None

            logger.info("SEARCH '{}' [res={}, t={}, p={}x{}, ext={}] by {}{}"
                        .format(q, results, took, page, per_page, str(extensions),
                                request.remote_addr, "_" + forwarded_for if forwarded_for else ""))

            db.log_search(request.remote_addr, forwarded_for, q, extensions, page, blocked, results, took)
            if blocked:
                return redirect("/search")
        else:
            flash("<strong>Error:</strong> Invalid captcha please try again", "danger")

    else:
        hits = None

    return render_template("search.html",
                           results=hits,
                           q=q,
                           p=page, per_page=per_page,
                           sort_order=sort_order,
                           results_set=config.RESULTS_PER_PAGE,
                           extensions=",".join(extensions),
                           size_min=size_min, size_max=size_max,
                           match_all=match_all,
                           field_trigram=field_trigram, field_path=field_path, field_name=field_name,
                           date_min=date_min, date_max=date_max,
                           show_captcha=config.CAPTCHA_SEARCH, recaptcha=recaptcha_search)


@app.route("/contribute")
@cache.cached(600)
def contribute():
    return render_template("contribute.html")


@app.route("/")
@cache.cached(240)
def home():
    try:
        stats = searchEngine.get_global_stats()
        stats["website_count"] = len(db.get_all_websites())
    except:
        stats = {}
    return render_template("home.html", stats=stats,
                           show_captcha=config.CAPTCHA_SEARCH, recaptcha=recaptcha_search)


@app.route("/submit")
def submit():
    queued_websites = taskManager.get_queued_tasks()[:30]
    return render_template("submit.html", queue=queued_websites, recaptcha=recaptcha,
                           show_captcha=config.CAPTCHA_SUBMIT)


def try_enqueue(url):
    url = os.path.join(url, "")
    url = od_util.get_top_directory(url)

    if not od_util.is_valid_url(url):
        return "<strong>Error:</strong> Invalid url. Make sure to include the appropriate scheme.", "warning"

    website = db.get_website_by_url(url)
    if website:
        return "Website already exists", "danger"

    website = db.website_exists(url)
    if website:
        return "A parent directory of this url has already been posted", "danger"

    if db.is_blacklisted(url):
        return "<strong>Error:</strong> " \
               "Sorry, this website has been blacklisted. If you think " \
               "this is an error, please <a href='/contribute'>contact me</a>.", "danger"

    if not od_util.is_od(url):
        return "<strong>Error:</strong>" \
               "The anti-spam algorithm determined that the submitted url is not " \
               "an open directory or the server is not responding. If you think " \
               "this is an error, please <a href='/contribute'>contact me</a>.", "danger"

    website_id = db.insert_website(Website(url, str(request.remote_addr + "_" +
                                                    request.headers.get("X-Forwarded-For", "")),
                                           request.user_agent))

    task = Task(website_id, url, priority=1)
    taskManager.queue_task(task)

    return "The website has been added to the queue", "success"


@app.route("/enqueue", methods=["POST"])
def enqueue():
    if not config.CAPTCHA_SUBMIT or recaptcha.verify():

        url = os.path.join(request.form.get("url"), "")
        message, msg_type = try_enqueue(url)
        flash(message, msg_type)

        return redirect("/submit")

    else:
        flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
        return redirect("/submit")


def check_url(url):
    url = os.path.join(url, "")
    try_enqueue(url)
    return None


@app.route("/enqueue_bulk", methods=["POST"])
def enqueue_bulk():
    if not config.CAPTCHA_SUBMIT or recaptcha.verify():

        urls = request.form.get("urls")
        if urls:
            urls = urls.split()

            if 0 < len(urls) <= 1000:  # TODO: Load from config & adjust placeholder/messages?

                pool = Pool(processes=6)
                pool.map(func=check_url, iterable=urls)
                pool.close()

                flash("Submitted websites to the queue", "success")

                return redirect("/submit")

            else:
                flash("Too few or too many urls, please submit 1-10 urls", "danger")
                return redirect("/submit")
        else:
            flash("Too few or too many urls, please submit 1-10 urls", "danger")
            return redirect("/submit")
    else:
        flash("<strong>Error:</strong> Invalid captcha please try again", "danger")
        return redirect("/submit")


@app.route("/admin")
def admin_login_form():
    if "username" in session:
        return redirect("/dashboard")
    return render_template("admin.html", recaptcha=recaptcha, show_captcha=config.CAPTCHA_LOGIN)


@app.route("/login", methods=["POST"])
def admin_login():
    if not config.CAPTCHA_LOGIN or recaptcha.verify():

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
        blacklist = db.get_blacklist()

        return render_template("dashboard.html", api_tokens=tokens, blacklist=blacklist)
    else:
        return abort(403)


@app.route("/blacklist/add", methods=["POST"])
def admin_blacklist_add():
    if "username" in session:

        url = request.form.get("url")
        db.add_blacklist_website(url)
        flash("Added item to blacklist", "success")
        return redirect("/dashboard")

    else:
        return abort(403)


@app.route("/blacklist/<int:blacklist_id>/delete")
def admin_blacklist_remove(blacklist_id):
    if "username" in session:
        db.remove_blacklist_website(blacklist_id)
        flash("Removed blacklist item", "success")
        return redirect("/dashboard")


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


# TODO: pages scrolling
@app.route("/logs", methods=["GET"])
def admin_crawl_logs():
    if "username" in session:

        results = db.get_crawl_logs()

        return render_template("crawl_logs.html", logs=results)
    else:
        return abort(403)


@app.route("/api/task/get", methods=["POST"])
def api_get_task():
    token = request.form.get("token")
    name = db.check_api_token(token)
    accept_ftp = request.form.get("accept") == "ftp" if "accept" in request.form else False

    if name:
        task = db.pop_task(name, accept_ftp)
        logger.debug("API get task from " + name)

        if task:
            logger.info("Assigning task " + str(task.to_json()) + " to " + name)
        else:
            logger.info("No queued tasks, creating a new one")

            try:
                website_id = db.get_oldest_website_id()
                website = db.get_website_by_id(website_id)
                task = Task(website_id, website.url)
                db.put_task(task)

                task = db.pop_task(name, accept_ftp)
            except:
                logger.error("Couldn't create new task")
                abort(404)

        return Response(str(task), mimetype="application/json")
    else:
        return abort(403)


@app.route("/api/task/cancel", methods=["POST"])
def api_cancel_task():
    token = request.form.get("token")
    name = db.check_api_token(token)

    if name:
        website_id = request.form.get("website_id") if "website_id" in request.form else None
        if website_id:
            logger.debug("API task cancel for " + str(website_id) + " by " + name)
            db.delete_task(website_id)
            return Response("cancelled task")
        else:
            abort(400)

    else:
        abort(403)


@app.route("/api/task/complete", methods=["POST"])
def api_complete_task():
    token = request.form.get("token")
    name = db.check_api_token(token)

    if name:
        tr = json.loads(request.form.get("result"))
        logger.debug("Task result: " + str(tr))
        task_result = TaskResult(tr["status_code"], tr["file_count"], tr["start_time"], tr["end_time"],
                                 tr["website_id"])

        logger.info("Task for " + str(task_result.website_id) + " completed by " + name)
        task = db.complete_task(task_result.website_id, name)

        if task:

            filename = "./tmp/" + str(task_result.website_id) + ".json"
            if not os.path.exists(filename):
                filename = None
            taskManager.complete_task(filename, task, task_result, name)

            if filename and os.path.exists(filename):
                os.remove(filename)

            # Handle task callback
            callback = PostCrawlCallbackFactory.get_callback(task)
            if callback:
                callback.run(task_result, search)

            return "Successfully logged task result and indexed files"

        else:
            logger.error("ERROR: " + name + " indicated that task for " + str(task_result.website_id) +
                         " was completed but there is no such task in the database.")
            return "No such task"
    return abort(403)


@app.route("/api/task/upload", methods=["POST"])
def api_upload():
    token = request.form.get("token")
    name = db.check_api_token(token)

    if name:
        website_id = request.form.get("website_id")
        logger.debug("Result part upload for '" + str(website_id) + "' by " + name)

        if "file_list" in request.files:
            file = request.files['file_list']

            filename = "./tmp/" + str(website_id) + ".json"

            # Read the file into memory cuz if the request fails
            # no file is corrupted.
            buf = file.stream.read()

            # Write to file (create if not exists) when
            # everything read successfully.
            with uploadLock:
                with open(filename, "a+b") as f:
                    f.write(buf)

            logger.debug("Written chunk to file")
        return "ok"
    else:
        return abort(403)


@app.route("/api/website/by_url", methods=["GET"])
def api_website_by_url():
    token = request.args.get("token")
    name = db.check_api_token(token)

    if name:
        url = request.args.get("url")
        website = db.get_website_by_url(url)
        logger.info("API get website by url '" + url + "' by " + name)
        if website:
            return str(website.id)
        return abort(404)
    else:
        return abort(403)


@app.route("/api/website/blacklisted", methods=["GET"])
def api_website_is_blacklisted():
    token = request.args.get("token")
    url = request.args.get("url")
    name = db.check_api_token(token)

    if name:
        logger.info("API get website is blacklisted '" + url + "' by " + name)
        return str(db.is_blacklisted(url))
    else:
        return abort(403)


@app.route("/api/website/add", methods=["GET"])
def api_add_website():
    token = request.args.get("token")
    url = request.args.get("url")

    name = db.check_api_token(token)
    if name:

        website_id = db.insert_website(Website(url, str(request.remote_addr + "_" +
                                                        request.headers.get("X-Forwarded-For", "")),
                                               "API_CLIENT_" + name))
        logger.info("API add website '" + url + "' by " + name + "(" + str(website_id) + ")")
        return str(website_id)
    else:
        return abort(403)


@app.route("/api/task/force_enqueue", methods=["POST"])
def api_task_enqueue():
    try:
        token = request.json["token"]
    except KeyError:
        return abort(400)

    name = db.check_api_token(token)

    if name:

        task = Task(
            request.json["website_id"],
            request.json["url"],
            request.json["priority"],
            request.json["callback_type"],
            json.dumps(request.json["callback_args"])
        )

        logger.info("API force enqueue by " + name + "\n(" + str(task.to_json()) + ")")

        taskManager.queue_task(task)
        return ""
    else:
        return abort(403)


@app.route("/api/task/try_enqueue", methods=["POST"])
def api_task_try_enqueue():
    token = request.form.get("token")
    name = db.check_api_token(token)

    if name:

        url = request.form.get("url")
        message, result = try_enqueue(url)

        logger.info("API try enqueue '" + url + "' by " + name + " (" + message + ")")

        return json.dumps({
            "message": message,
            "result": result
        })
    else:
        return abort(403)


@app.route("/api/website/random")
def api_random_website():
    token = request.json["token"]
    name = db.check_api_token(token)

    if name:
        logger.info("API get random website by " + name)
        return str(db.get_random_website_id())
    else:
        return abort(403)


@app.route("/api/search", methods=["POST"])
def api_search():
    token = request.json["token"]
    name = db.check_api_token(token)

    if name:

        try:
            hits = searchEngine.search(
                request.json["query"],
                request.json["page"], request.json["per_page"],
                request.json["sort_order"],
                request.json["extensions"],
                request.json["size_min"], request.json["size_max"],
                request.json["match_all"],
                request.json["fields"],
                request.json["date_min"], request.json["date_max"]
            )

            hits = db.join_website_on_search_result(hits)
            logger.info("API search '" + request.json["query"] + "' by " + name)
            return json.dumps(hits)

        except InvalidQueryException as e:
            logger.info("API search failed: " + str(e))
            return str(e)
    else:
        return abort(403)


if __name__ == '__main__':
    app.run("0.0.0.0", port=12345, threaded=True)
