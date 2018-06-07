# OD-Database

Suggestions/concerns/PRs are welcome

## Installation
Assuming you have Python 3 and git installed:
```bash
git clone https://github.com/simon987/od-database
cd od-database
pip3 install -r requirements.txt
```
Create `/config.py` and fill out the parameters. Empty config:
```python
CAPTCHA_SITE_KEY = ""
CAPTCHA_SECRET_KEY = ""
FLASK_SECRET = ""
USE_SSL = True
RESULTS_PER_PAGE = (25, 50, 100, 250, 500, 1000)
```

## Running
```bash
python3 app.py
```
You should be able to connect with your browser at `https://localhost:12345`

*_Note: To use SSL you have to put the appropriate certificates in /certificates/_
