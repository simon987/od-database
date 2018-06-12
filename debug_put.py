import requests
import json


payload = json.dumps({
    "url": "http://138.197.215.189/",
    "priority": 2,
    "callback_type": "",
    "callback_args": "{}"
})

r = requests.post("http://localhost:5000/task/put",
                  headers={"Content-Type": "application/json"},
                  data=payload)