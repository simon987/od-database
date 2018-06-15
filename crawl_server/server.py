from flask import Flask, request, abort, Response, send_file
from flask_httpauth import HTTPTokenAuth
import json
from crawl_server.task_manager import TaskManager, Task
import os
import config
app = Flask(__name__)
auth = HTTPTokenAuth(scheme="Token")

tokens = [config.CRAWL_SERVER_TOKEN]

tm = TaskManager("tm_db.sqlite3", 64)


@auth.verify_token
def verify_token(token):
    if token in tokens:
        return True


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
        except KeyError:
            return abort(400)

        task = Task(website_id, url, priority, callback_type, callback_args)
        tm.put_task(task)
        return '{"ok": "true"}'

    return abort(400)


@app.route("/task/completed", methods=["GET"])
@auth.login_required
def get_completed_tasks():
    json_str = json.dumps([result.to_json() for result in tm.get_non_indexed_results()])
    return json_str


@app.route("/task/current", methods=["GET"])
@auth.login_required
def get_current_tasks():

    current_tasks = tm.get_current_tasks()
    return json.dumps([t.to_json() for t in current_tasks])


@app.route("/file_list/<int:website_id>/")
@auth.login_required
def get_file_list(website_id):

    file_name = "./crawled/" + str(website_id) + ".json"
    if os.path.exists(file_name):
        return send_file(file_name)
    else:
        return abort(404)


if __name__ == "__main__":
    app.run(port=5001, host="0.0.0.0")
