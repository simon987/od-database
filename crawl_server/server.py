from flask import Flask, request, abort, Response
import json
from crawl_server.task_manager import TaskManager, Task, TaskResult
app = Flask(__name__)

tm = TaskManager("tm_db.sqlite3")


@app.route("/task/")
def get_tasks():
    json_str = json.dumps([task.to_json() for task in tm.get_tasks()])
    return Response(json_str, mimetype="application/json")


@app.route("/task/put", methods=["POST"])
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
def get_completed_tasks():
    json_str = json.dumps([result.to_json() for result in tm.get_non_indexed_results()])
    return json_str


@app.route("/task/current", methods=["GET"])
def get_current_tasks():

    current_tasks = tm.get_current_tasks()
    return current_tasks


if __name__ == "__main__":
    app.run(port=5001)
