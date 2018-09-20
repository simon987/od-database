# OD-Database

OD-Database is a web-crawling project that aims to index a very large number of file links and their basic metadata from open directories (misconfigured Apache/Nginx/FTP servers, or more often, mirrors of various public services).

Each crawler instance fetches tasks from the central server and pushes the result once completed. A single instance can crawl hundreds of websites at the same time (Both FTP and HTTP(S)) and the central server is capable of ingesting thousands of new documents per second. 

The data is indexed into elasticsearch and made available via the web frontend (Currently hosted at https://od-db.the-eye.eu/). There is currently ~1.93 billion files indexed (total of about 300Gb of raw data). The raw data is made available as a CSV file [here](https://od-db.the-eye.eu/dl).

![2018-09-20-194116_1127x639_scrot](https://user-images.githubusercontent.com/7120851/45852325-281cca00-bd0d-11e8-9fed-49a54518e972.png)


### Contributing   
Suggestions/concerns/PRs are welcome

## Installation
Assuming you have Python 3 and git installed:
```bash
sudo apt install libssl-dev libcurl4-openssl-dev
git clone https://github.com/simon987/od-database
cd od-database
sudo pip3 install -r requirements.txt
```
Create `/config.py` and fill out the parameters. Sample config:
```python
# Leave default values for no CAPTCHAs
CAPTCHA_LOGIN = False
CAPTCHA_SUBMIT = False
CAPTCHA_SEARCH = False
CAPTCHA_SITE_KEY = ""
CAPTCHA_SECRET_KEY = ""
CAPTCHA_S_SITE_KEY = ""
CAPTCHA_S_SECRET_KEY = ""

# Flask secret key for sessions
FLASK_SECRET = ""
RESULTS_PER_PAGE = (25, 50, 100, 250, 500, 1000)
# Headers for http crawler
HEADERS = {}
# Number of crawler instances (one per task)
CRAWL_SERVER_PROCESSES = 3
# Number of threads per crawler instance
CRAWL_SERVER_THREADS = 20
# Allow ftp websites in /submit
SUBMIT_FTP = False
# Allow http(s) websites in /submit
SUBMIT_HTTP = True

SERVER_URL = "http://localhost/api"
API_TOKEN = "5817926d-f2f9-4422-a411-a98f1bfe4b6c"
```

## Running the crawl server
```bash
cd od-database
export PYTHONPATH=$(pwd)
cd crawl_server
python3 run.py
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

