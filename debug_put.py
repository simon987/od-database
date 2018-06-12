import requests
import json


payload = json.dumps({
    "website_id": 123,
    "url": "http://liminaire.fr/TEXTES/",
    "priority": 2,
    "callback_type": "",
    "callback_args": "{}"
})

r = requests.post("http://localhost:5001/task/put",
                  headers={"Content-Type": "application/json"},
                  data=payload)
