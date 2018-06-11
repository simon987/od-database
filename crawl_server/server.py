from flask import Flask, request, abort, Response
import json
from crawl_server.task_manager import TaskManager, Task
app = Flask(__name__)

tm = TaskManager("tm_db.sqlite3")


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/task/")
def get_tasks():
    json_str = json.dumps([task.to_json() for task in tm.get_tasks()])
    return Response(json_str, mimetype="application/json")


@app.route("/task/put", methods=["POST"])
def task_put():

    if request.json:
        try:
            url = request.json["url"]
            priority = request.json["priority"]
            callback_type = request.json["callback_type"]
            callback_args = request.json["callback_args"]
        except KeyError:
            return abort(400)

        task = Task(url, priority, callback_type, callback_args)
        tm.put_task(task)
        return '{"ok": "true"}'

    return abort(400)


if __name__ == "__main__":
    app.run()
