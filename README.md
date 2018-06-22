# OD-Database

Suggestions/concerns/PRs are welcome

## Installation
Assuming you have Python 3 and git installed:
```bash
git clone https://github.com/simon987/od-database
cd od-database
sudo pip3 install -r requirements.txt
```
Create `/config.py` and fill out the parameters. Sample config:
```python
CAPTCHA_SITE_KEY = ""
CAPTCHA_SECRET_KEY = ""
FLASK_SECRET = ""
RESULTS_PER_PAGE = (25, 50, 100, 250, 500, 1000)
CRAWL_SERVER_HEADERS = {}
CRAWL_SERVER_TOKEN = ""
CRAWL_SERVER_PORT = 5001
CRAWL_SERVER_PROCESSES = 3
CRAWL_SERVER_THREADS = 20

```

## Running the crawl server
```bash
cd od-database
export PYTHONPATH=$(pwd)
cd crawl_server
python3 server.py
```
