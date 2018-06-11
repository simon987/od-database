import requests
import json


payload = json.dumps({
    "url": "http://124.158.108.137/ebooks/",
    "priority": 2,
    "callback_type": "",
    "callback_args": "{}"
})

r = requests.post("http://localhost:5000/task/put",
                  headers={"Content-Type": "application/json"},
                  data=payload)