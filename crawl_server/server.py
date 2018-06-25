from flask import Flask, request, abort, Response, send_file
from flask_httpauth import HTTPTokenAuth
import json
from crawl_server import logger
from crawl_server.task_manager import TaskManager, Task
import os
import config
app = Flask(__name__)
auth = HTTPTokenAuth(scheme="Token")

token = config.CRAWL_SERVER_TOKEN

tm = TaskManager("tm_db.sqlite3", config.CRAWL_SERVER_PROCESSES)


@auth.verify_token
def verify_token(provided_token):
    return token == provided_token


@app.route("/task/")
@auth.login_required
def get_tasks():
    json_str = json.dumps([task.to_json() for task in tm.get_tasks()])
    return Response(json_str, mimetype="application/json")


@app.route("/task/put", methods=["POST"])
@auth.login_required
def task_put():

    if request.json:
        try:
            website_id = request.json["website_id"]
            url = request.json["url"]
            priority = request.json["priority"]
            callback_type = request.json["callback_type"]
            callback_args = request.json["callback_args"]
        except KeyError as e:
            logger.error("Invalid task put request from " + request.remote_addr + " missing key: " + str(e))
            return abort(400)

        task = Task(website_id, url, priority, callback_type, callback_args)
        tm.put_task(task)
        logger.info("Submitted new task to queue: " + str(task.to_json()))
        return '{"ok": "true"}'

    return abort(400)


@app.route("/task/completed", methods=["GET"])
@auth.login_required
def get_completed_tasks():
    json_str = json.dumps([result.to_json() for result in tm.get_non_indexed_results()])
    logger.debug("Webserver has requested list of newly completed tasks from " + request.remote_addr)
    return Response(json_str, mimetype="application/json")


@app.route("/task/current", methods=["GET"])
@auth.login_required
def get_current_tasks():

    current_tasks = tm.get_current_tasks()
    logger.debug("Webserver has requested list of current tasks from " + request.remote_addr)
    return json.dumps([t.to_json() for t in current_tasks])


@app.route("/file_list/<int:website_id>/")
@auth.login_required
def get_file_list(website_id):

    file_name = "./crawled/" + str(website_id) + ".json"
    if os.path.exists(file_name):
        logger.info("Webserver requested file list of website with id" + str(website_id))
        return send_file(file_name)
    else:
        logger.error("Webserver requested file list of non-existent or empty website with id: " + str(website_id))
        return abort(404)


@app.route("/file_list/<int:website_id>/free")
@auth.login_required
def free_file_list(website_id):
    file_name = "./crawled/" + str(website_id) + ".json"
    if os.path.exists(file_name):
        os.remove(file_name)
        logger.debug("Webserver indicated that the files for the website with id " +
                      str(website_id) + " are safe to delete")
        return '{"ok": "true"}'
    else:
        return abort(404)


@app.route("/task/pop_all")
@auth.login_required
def pop_queued_tasks():

    json_str = json.dumps([task.to_json() for task in tm.pop_tasks()])
    logger.info("Webserver poped all queued tasks")
    return Response(json_str, mimetype="application/json")


if __name__ == "__main__":
    app.run(port=config.CRAWL_SERVER_PORT, host="0.0.0.0", ssl_context="adhoc")
