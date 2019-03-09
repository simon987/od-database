import json
import os
from threading import Lock
from uuid import uuid4

from flask import request, abort, Response, send_file, session

import common as oddb
import captcha
from callbacks import PostCrawlCallbackFactory
from database import Task, Website
from search.search import InvalidQueryException
from tasks import TaskResult

uploadLock = Lock()


def setup_api(app):
    @app.route("/api/task/complete", methods=["POST"])
    def api_complete_task():
        # TODO: task_tracker
        token = request.form.get("token")
        name = oddb.db.check_api_token(token)

        if name:
            tr = json.loads(request.form.get("result"))
            oddb.logger.debug("Task result: " + str(tr))
            task_result = TaskResult(tr["status_code"], tr["file_count"], tr["start_time"], tr["end_time"],
                                     tr["website_id"])

            oddb.logger.info("Task for " + str(task_result.website_id) + " completed by " + name)
            task = oddb.db.complete_task(task_result.website_id, name)

            if task:

                filename = "./tmp/" + str(task_result.website_id) + ".json"
                if not os.path.exists(filename):
                    filename = None
                oddb.taskManager.complete_task(filename, task, task_result, name)

                if filename and os.path.exists(filename):
                    os.remove(filename)

                # Handle task callback
                callback = PostCrawlCallbackFactory.get_callback(task)
                if callback:
                    callback.run(task_result, oddb.search)

                return "Successfully logged task result and indexed files"

            else:
                oddb.logger.error("ERROR: " + name + " indicated that task for " + str(task_result.website_id) +
                                  " was completed but there is no such task in the database.")
                return "No such task"
        return abort(403)

    @app.route("/api/task/upload", methods=["POST"])
    def api_upload():
        token = request.form.get("token")
        name = oddb.db.check_api_token(token)

        if name:
            website_id = request.form.get("website_id")
            oddb.logger.debug("Result part upload for '" + str(website_id) + "' by " + name)

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

                oddb.logger.debug("Written chunk to file")
            return "ok"
        else:
            return abort(403)

    @app.route("/api/website/by_url", methods=["GET"])
    def api_website_by_url():
        token = request.args.get("token")
        name = oddb.db.check_api_token(token)

        if name:
            url = request.args.get("url")
            website = oddb.db.get_website_by_url(url)
            oddb.logger.info("API get website by url '" + url + "' by " + name)
            if website:
                return str(website.id)
            return abort(404)
        else:
            return abort(403)

    @app.route("/api/website/blacklisted", methods=["GET"])
    def api_website_is_blacklisted():
        token = request.args.get("token")
        url = request.args.get("url")
        name = oddb.db.check_api_token(token)

        if name:
            oddb.logger.info("API get website is blacklisted '" + url + "' by " + name)
            return str(oddb.db.is_blacklisted(url))
        else:
            return abort(403)

    @app.route("/api/website/add", methods=["GET"])
    def api_add_website():
        token = request.args.get("token")
        url = request.args.get("url")

        name = oddb.db.check_api_token(token)
        if name:

            website_id = oddb.db.insert_website(Website(url, str(request.remote_addr + "_" +
                                                                 request.headers.get("X-Forwarded-For", "")),
                                                        "API_CLIENT_" + name))
            oddb.logger.info("API add website '" + url + "' by " + name + "(" + str(website_id) + ")")
            return str(website_id)
        else:
            return abort(403)

    @app.route("/api/task/force_enqueue", methods=["POST"])
    def api_task_enqueue():
        try:
            token = request.json["token"]
        except KeyError:
            return abort(400)

        name = oddb.db.check_api_token(token)

        if name:

            task = Task(
                request.json["website_id"],
                request.json["url"],
                request.json["priority"],
                request.json["callback_type"],
                json.dumps(request.json["callback_args"])
            )

            oddb.logger.info("API force enqueue by " + name + "\n(" + str(task.to_json()) + ")")

            oddb.taskManager.queue_task(task)
            return ""
        else:
            return abort(403)

    @app.route("/api/task/try_enqueue", methods=["POST"])
    def api_task_try_enqueue():
        token = request.form.get("token")
        name = oddb.db.check_api_token(token)

        if name:

            url = request.form.get("url")
            # TODO: task_tracker
            message, result = oddb.try_enqueue(url)

            oddb.logger.info("API try enqueue '" + url + "' by " + name + " (" + message + ")")

            return json.dumps({
                "message": message,
                "result": result
            })
        else:
            return abort(403)

    @app.route("/api/website/random")
    def api_random_website():
        token = request.json["token"]
        name = oddb.db.check_api_token(token)

        if name:
            oddb.logger.info("API get random website by " + name)
            return str(oddb.db.get_random_website_id())
        else:
            return abort(403)

    @app.route("/api/search", methods=["POST"])
    def api_search():
        token = request.json["token"]
        name = oddb.db.check_api_token(token)

        if name:

            try:
                hits = oddb.searchEngine.search(
                    request.json["query"],
                    request.json["page"], request.json["per_page"],
                    request.json["sort_order"],
                    request.json["extensions"],
                    request.json["size_min"], request.json["size_max"],
                    request.json["match_all"],
                    request.json["fields"],
                    request.json["date_min"], request.json["date_max"]
                )

                hits = oddb.db.join_website_on_search_result(hits)
                oddb.logger.info("API search '" + request.json["query"] + "' by " + name)
                return json.dumps(hits)

            except InvalidQueryException as e:
                oddb.logger.info("API search failed: " + str(e))
                return str(e)
        else:
            return abort(403)

    @app.route("/cap", methods=["GET"])
    def cap():
        word = captcha.make_captcha()
        cap_id = uuid4()
        session["cap"] = cap_id
        oddb.sessionStore[cap_id] = word

        return send_file(captcha.get_path(word), cache_timeout=0)

