import os
import json
import sqlite3


class TaskResult:

    def __init__(self, status_code=None, file_count=0, start_time=0, end_time=0, website_id=0):
        self.status_code = status_code
        self.file_count = file_count
        self.start_time = start_time
        self.end_time = end_time
        self.website_id = website_id

    def to_json(self):
        return {
            "status_code": self.status_code,
            "file_count": self.file_count,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "website_id": self.website_id
        }


class Task:

    def __init__(self, website_id: int, url: str, priority: int = 1,
                 callback_type: str = None, callback_args: str = None):
        self.website_id = website_id
        self.url = url
        self.priority = priority
        self.callback_type = callback_type
        self.callback_args = json.loads(callback_args) if callback_args else {}

    def to_json(self):
        return {
            "website_id": self.website_id,
            "url": self.url,
            "priority": self.priority,
            "callback_type": self.callback_type,
            "callback_args": json.dumps(self.callback_args)
        }

    def __repr__(self):
        return json.dumps(self.to_json())


class TaskManagerDatabase:

    def __init__(self, db_path):
        self.db_path = db_path

        if not os.path.exists(db_path):
            self.init_database()

    def init_database(self):

        with open("task_db_init.sql", "r") as f:
            init_script = f.read()

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(init_script)
            conn.commit()

    def pop_task(self):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, website_id, url, priority, callback_type, callback_args"
                           " FROM Queue ORDER BY priority DESC, Queue.id ASC LIMIT 1")
            task = cursor.fetchone()

            if task:
                cursor.execute("DELETE FROM Queue WHERE id=?", (task[0],))
                conn.commit()
                return Task(task[1], task[2], task[3], task[4], task[5])
            else:
                return None

    def put_task(self, task: Task):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("INSERT INTO Queue (website_id, url, priority, callback_type, callback_args) "
                           "VALUES (?,?,?,?,?)",
                           (task.website_id, task.url, task.priority,
                            task.callback_type, json.dumps(task.callback_args)))
            conn.commit()

    def get_tasks(self):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT website_id, url, priority, callback_type, callback_args FROM Queue")
            tasks = cursor.fetchall()

            return [Task(t[0], t[1], t[2], t[3], t[4]) for t in tasks]

    def log_result(self, result: TaskResult):

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("INSERT INTO TaskResult (website_id, status_code, file_count, start_time, end_time) "
                           "VALUES (?,?,?,?,?)", (result.website_id, result.status_code, result.file_count,
                                                  result.start_time, result.end_time))
            conn.commit()

    def get_non_indexed_results(self):
        """Get a list of new TaskResults since the last call of this method"""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT status_code, file_count, start_time, end_time, website_id"
                           " FROM TaskResult WHERE indexed_time != NULL")
            db_result = cursor.fetchall()

            cursor.execute("UPDATE TaskResult SET indexed_time = CURRENT_TIMESTAMP")

            return [TaskResult(r[0], r[1], r[2], r[3], r[4]) for r in db_result]
