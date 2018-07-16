import requests
import json


payload = json.dumps({
    "token": "4eafc6ed-74b7-4f04-9d34-7f3e01201003",
    "website_id": 3,
    "url": "http://localhost:8000/",
    "priority": 2,
    "callback_type": "",
    "callback_args": "{}"
})

r = requests.post("http://localhost/api/task/enqueue",
                  headers={"Content-Type": "application/json"},
                  data=payload)
print(r)
print(r.text)
