import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import os
import validators
import re
import mimetypes
from ftplib import FTP


def truncate_path(path, max_len):
    pattern = re.compile(r"/?.*?/")

    for i in range(1, path.count("/")):
        new_path = pattern.sub(".../", path, i)
        if len(new_path) < max_len:
            return new_path
    return ".../" + path.rsplit("/", maxsplit=1)[1] if "/" in path else path


colors = {
    "application": "bg-application",
    "text": "bg-text",
    "video": "bg-video",
    "image": "bg-image",
    "audio": "bg-audio"
}


def get_color(mime):
    return colors.get(mime.split("/", maxsplit=1)[0], None)


def get_mime(file_name):
    mime = mimetypes.guess_type(file_name)
    if mime[0]:
        return mime[0]
    else:
        return None


def is_valid_url(url):
    if not url.endswith("/"):
        return False

    if not url.startswith(("http://", "https://", "ftp://")):
        return False

    return validators.url(url)


def has_extension(link):
    return len(os.path.splitext(link)[1]) > 0


def is_external_link(base_url, url: str):
    url = urljoin(base_url, url).strip()

    if base_url in url:
        return False
    return True


def is_od(url):

    if not url.endswith("/"):
        print("Url does not end with trailing /")
        return False

    try:
        if url.startswith("ftp://"):
            url = url[6:-1]  # Remove schema and trailing slash
            ftp = FTP(url)
            ftp.login()
            ftp.close()
            return True
        else:
            r = requests.get(url, timeout=30, allow_redirects=False)
            if r.status_code != 200:
                print("No redirects allowed!")
                return False
            soup = BeautifulSoup(r.text, "lxml")

            external_links = sum(1 if is_external_link(url, a.get("href")) else 0 for a in soup.find_all("a"))
            link_tags = len(list(soup.find_all("link")))
            script_tags = len(list(soup.find_all("script")))

            if external_links > 11:
                print("Too many external links!")
                return False

            if link_tags > 5:
                print("Too many link tags!")
                return False

            if script_tags > 7:
                print("Too many script tags!")
                return False

            return True

    except Exception as e:
        print(e)
        return False


def is_blacklisted(url):

    with open("blacklist.txt", "r") as f:
        for line in f.readlines():
            if url.startswith(line.strip()):
                return True

    return False
