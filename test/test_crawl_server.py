from flask_testing import LiveServerTestCase
import json
import requests
from crawl_server.server import app


class CrawlServerTest(LiveServerTestCase):

    headers = {
        "Content-Type": "application/json"
    }

    HOST = "http://localhost:9999"

    def create_app(self):

        self.app = app
        app.config['LIVESERVER_PORT'] = 9999
        return app

    def test_put_task(self):

        payload = json.dumps({
            "url": "a",
            "priority": 2,
            "callback_type": "c",
            "callback_args": '{"d": 4}'
        })

        requests.post(self.HOST + "/task/put", data=payload, headers=self.headers)

        r = requests.get(self.HOST + "/task")
        self.assertEqual(200, r.status_code)

        result = json.loads(r.text)[0]
        self.assertEqual(result["url"], "a")
        self.assertEqual(result["priority"], 2)
        self.assertEqual(result["callback_type"], "c")
        self.assertEqual(result["callback_args"], '{"d": 4}')

        payload = json.dumps({"url": "", "priority": 1, "callback_type": "", "callback_args": "{}"})
        r = requests.post(self.HOST + "/task/put", data=payload)
        self.assertEqual(400, r.status_code)

        r2 = requests.post(self.HOST + "/task/put", headers=self.headers, data=payload)
        self.assertEqual(200, r2.status_code)
