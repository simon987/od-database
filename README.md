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
HEADERS = {}
CRAWL_SERVER_TOKEN = ""
CRAWL_SERVER_PORT = 5001
CRAWL_SERVER_PROCESSES = 3
CRAWL_SERVER_THREADS = 20
SUBMIT_FTP = False
SUBMIT_HTTP = True
```

## Running the crawl server
```bash
cd od-database
export PYTHONPATH=$(pwd)
cd crawl_server
python3 server.py
```
## Running the web server (development)
```bash
cd od-database
python3 app.py
```

## Running the web server with nginx (production)
* Install dependencies:
```bash
sudo apt install build-essential python-dev
sudo pip install uwsgi
```
* Adjust the path in `od-database.ini`
* Configure nginx (on Debian 9: `/etc/nginx/sites-enabled/default`):
```nginx
server {
        ...

        include uwsgi_params;
        location / {
                uwsgi_pass 127.0.0.1:3031;
        }
        
        ...
}
```
* Start uwsgi:
```bash
uwsgi od-database.ini
```

