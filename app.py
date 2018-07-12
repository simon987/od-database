from flask import Flask, render_template, redirect, request, flash, abort, Response, send_from_directory, session
import json
from urllib.parse import urlparse
import os
import time
import itertools
from database import Database, Website, InvalidQueryException
from flask_recaptcha import ReCaptcha
import od_util
import config
from flask_caching import Cache
from task import TaskDispatcher, Task, CrawlServer
from search.search import ElasticSearchEngine

app = Flask(__name__)
if config.CAPTCHA_SUBMIT or config.CAPTCHA_LOGIN:
    recaptcha = ReCaptcha(app=app,
                          site_key=config.CAPTCHA_SITE_KEY,
                          secret_key=config.CAPTCHA_SECRET_KEY)
else:
    recaptcha = None
app.secret_key = config.FLASK_SECRET
db = Database("db.sqlite3")
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.jinja_env.globals.update(truncate_path=od_util.truncate_path)
app.jinja_env.globals.update(get_color=od_util.get_color)
app.jinja_env.globals.update(get_mime=od_util.get_category)

taskDispatcher = TaskDispatcher()
searchEngine = ElasticSearchEngine("od-database")


@app.template_filter("date_format")
def datetime_format(value, format='%Y-%m-%d'):
    return time.strftime(format, time.gmtime(value))


@app.template_filter("datetime_format")
def datetime_format(value, format='%Y-%m-%d %H:%M:%S'):
    return time.strftime(format, time.gmtime(value))


@app.route("/dl")
def downloads():
    try:
        export_file_stats = os.stat("static/out.csv.xz")
    except FileNotFoundError:
        print("No export file")
        export_file_stats = None

    return render_template("downloads.html", export_file_stats=export_file_stats)


@app.route("/stats")
def stats_page():
    crawl_server_stats = db.get_stats_by_server()
    return render_template("stats.html", crawl_server_stats=crawl_server_stats)


@app.route("/stats/json_chart")
@cache.cached(240)
def stats_json():
    stats = searchEngine.get_global_stats()
    db.join_website_on_stats(stats)
    return Response(json.dumps(stats), mimetype="application/json")


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


@app.route("/website/redispatch_queued")
def admin_redispatch_queued():
    if "username" in session:

        count = taskDispatcher.redispatch_queued()
        flash("Re-dispatched " + str(count) + " tasks", "success")
        return redirect("/dashboard")

    else:
        abort(404)


def get_empty_websites():
    current_tasks = itertools.chain(taskDispatcher.get_queued_tasks(), taskDispatcher.get_current_tasks())

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


@app.route("/website/queue_empty")
def admin_queue_empty_websites():
    if "username" in session:

        for website_id in get_empty_websites():
            website = db.get_website_by_id(website_id)
            task = Task(website.id, website.url, 1)
            taskDispatcher.dispatch_task(task)
        flash("Dispatched empty websites", "success")
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
            taskDispatcher.dispatch_task(task)

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

        db.log_search(request.remote_addr,
                      request.headers["X-Forwarded-For"] if "X-Forwarded-For" in request.headers else None,
                      q, extensions, page)

        try:
            hits = searchEngine.search(q, page, per_page, sort_order,
                                       extensions, size_min, size_max, match_all, fields, date_min, date_max)
            hits = db.join_website_on_search_result(hits)
        except InvalidQueryException as e:
            flash("<strong>Invalid query:</strong> " + str(e), "warning")
            return redirect("/search")
        except Exception:
            flash("Query failed, this could mean that the search server is overloaded or is not reachable. "
                  "Please try again later", "danger")
            hits = None

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
                           date_min=date_min, date_max=date_max)


@app.route("/contribute")
def contribute():
    return render_template("contribute.html")


@app.route("/")
@cache.cached(240)
def home():
    try:
        stats = searchEngine.get_global_stats()
        stats["website_count"] = len(db.get_all_websites())
        current_websites = ", ".join(task.url for task in taskDispatcher.get_current_tasks())
    except:
        stats = {}
        current_websites = None
    return render_template("home.html", stats=stats, current_websites=current_websites)


@app.route("/submit")
def submit():
    queued_websites = taskDispatcher.get_queued_tasks()
    return render_template("submit.html", queue=queued_websites, recaptcha=recaptcha, show_captcha=config.CAPTCHA_SUBMIT)


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

    web_id = db.insert_website(Website(url, str(request.remote_addr), str(request.user_agent)))

    task = Task(web_id, url, priority=1)
    taskDispatcher.dispatch_task(task)

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


@app.route("/enqueue_bulk", methods=["POST"])
def enqueue_bulk():
    if not config.CAPTCHA_SUBMIT or recaptcha.verify():

        urls = request.form.get("urls")
        if urls:
            urls = urls.split()

            if 0 < len(urls) <= 1000000000000:

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
        crawl_servers = db.get_crawl_servers()

        return render_template("dashboard.html", api_tokens=tokens, blacklist=blacklist, crawl_servers=crawl_servers)
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


@app.route("/logs", methods=["GET"])
def admin_crawl_logs():
    if "username" in session:

        results = db.get_crawl_logs()

        return render_template("crawl_logs.html", logs=results)
    else:
        return abort(403)


@app.route("/crawl_server/add", methods=["POST"])
def admin_add_crawl_server():
    if "username" in session:

        server = CrawlServer(
            request.form.get("url"),
            request.form.get("name"),
            request.form.get("slots"),
            request.form.get("token")
        )

        db.add_crawl_server(server)
        flash("Added crawl server", "success")
        return redirect("/dashboard")

    else:
        return abort(403)


@app.route("/crawl_server/<int:server_id>/delete")
def admin_delete_crawl_server(server_id):
    if "username" in session:

        db.remove_crawl_server(server_id)
        flash("Deleted crawl server", "success")
        return redirect("/dashboard")

    else:
        abort(403)


@app.route("/crawl_server/<int:server_id>/update", methods=["POST"])
def admin_update_crawl_server(server_id):
    crawl_servers = db.get_crawl_servers()
    for server in crawl_servers:
        if server.id == server_id:
            new_slots = request.form.get("slots") if "slots" in request.form else server.slots
            new_name = request.form.get("name") if "name" in request.form else server.name
            new_url = request.form.get("url") if "url" in request.form else server.url

            db.update_crawl_server(server_id, new_url, new_name, new_slots)
            flash("Updated crawl server", "success")
            return redirect("/dashboard")

    flash("Couldn't find crawl server with this id: " + str(server_id), "danger")
    return redirect("/dashboard")


if __name__ == '__main__':
    app.run("0.0.0.0", port=12345, threaded=True)
