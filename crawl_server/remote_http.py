from crawl_server import logger
from urllib.parse import unquote, urljoin
import os
from html.parser import HTMLParser
from itertools import repeat
from crawl_server.crawler import RemoteDirectory, File
import requests
from requests.exceptions import RequestException
from multiprocessing.pool import ThreadPool
import config
from dateutil.parser import parse as parse_date
import hashlib

import urllib3
urllib3.disable_warnings()


class Anchor:
    def __init__(self):
        self.text = None
        self.href = None

    def __str__(self):
        return "<" + self.href + ", " + str(self.text).strip() + ">"


class HTMLAnchorParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.anchors = []
        self.current_anchor = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr in attrs:
                if attr[0] == "href":
                    self.current_anchor = Anchor()
                    self.current_anchor.href = attr[1]
                    break

    def handle_data(self, data):
        if self.current_anchor:
            self.current_anchor.text = data

    def handle_endtag(self, tag):
        if tag == "a":
            if self.current_anchor:
                self.anchors.append(self.current_anchor)
                self.current_anchor = None

    def error(self, message):
        logger.debug("HTML Parser error: " + message)

    def feed(self, data):
        self.anchors.clear()
        super().feed(data)


class HttpDirectory(RemoteDirectory):

    SCHEMES = ("http", "https",)
    HEADERS = config.HEADERS
    BLACK_LIST = (
        "?C=N&O=D",
        "?C=M&O=A",
        "?C=S&O=A",
        "?C=D&O=A",
        "?C=N;O=D",
        "?C=M;O=A",
        "?C=M&O=D",
        "?C=S;O=A",
        "?C=S&O=D",
        "?C=D;O=A",
        "?MA",
        "?SA",
        "?DA",
        "?ND",
        "?C=N&O=A",
        "?C=N&O=A",
        "?M=A",
        "?N=D",
        "?S=A",
        "?D=A",
    )
    FILE_NAME_BLACKLIST = (
        "Parent Directory",
        " Parent Directory"
        "../",

    )
    MAX_RETRIES = 2
    TIMEOUT = 1

    def __init__(self, url):
        super().__init__(url)
        self.session = requests.Session()
        self.session.headers = HttpDirectory.HEADERS
        self.session.verify = False
        self.session.max_redirects = 1

    def list_dir(self, path):

        current_dir_name = path[path.rstrip("/").rfind("/") + 1: -1]
        path_identifier = hashlib.sha1(current_dir_name.encode())
        path_url = urljoin(self.base_url, path, "")
        body = self._stream_body(path_url)
        anchors = self._parse_links(body)

        urls_to_request = []
        files = []

        for anchor in anchors:
            if self._should_ignore(self.base_url, path, anchor):
                continue

            if self._isdir(anchor):

                directory = File(
                    name=anchor.href,  # todo handle external links here
                    mtime=0,
                    size=0,
                    path=path,
                    is_dir=True
                )
                path_identifier.update(bytes(directory))
                files.append(directory)
            else:
                urls_to_request.append(urljoin(path_url, anchor.href))

        for file in self.request_files(urls_to_request):
            path_identifier.update(bytes(file))
            files.append(file)

        return path_identifier.hexdigest(), files

    def request_files(self, urls_to_request: list) -> list:

        if len(urls_to_request) > 150:
            # Many urls, use multi-threaded solution
            pool = ThreadPool(processes=10)
            files = pool.starmap(HttpDirectory._request_file, zip(repeat(self), urls_to_request))
            pool.close()
            for file in files:
                if file:
                    yield file
        else:
            # Too few urls to create thread pool
            for url in urls_to_request:
                file = self._request_file(url)
                if file:
                    yield file

    def _request_file(self, url):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = self.session.head(url, allow_redirects=False, timeout=HttpDirectory.TIMEOUT)

                stripped_url = url[len(self.base_url) - 1:]

                path, name = os.path.split(stripped_url)
                date = r.headers.get("Last-Modified", "1970-01-01")
                return File(
                    path=unquote(path).strip("/"),
                    name=unquote(name),
                    size=int(r.headers.get("Content-Length", -1)),
                    mtime=int(parse_date(date).timestamp()),
                    is_dir=False
                )
            except RequestException:
                self.session.close()
                retries -= 1

        logger.debug("TimeoutError - _request_file")
        raise TimeoutError

    def _stream_body(self, url: str):
        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = self.session.get(url, stream=True, timeout=HttpDirectory.TIMEOUT)
                for chunk in r.iter_content(chunk_size=8192):
                    try:
                        yield chunk.decode(r.encoding if r.encoding else "utf-8", errors="ignore")
                    except LookupError:
                        # Unsupported encoding
                        yield chunk.decode("utf-8", errors="ignore")
                r.close()
                return
            except RequestException:
                self.session.close()
                retries -= 1

        logger.debug("TimeoutError - _stream_body")
        raise TimeoutError

    @staticmethod
    def _parse_links(body):

        parser = HTMLAnchorParser()
        anchors = []

        for chunk in body:
            parser.feed(chunk)
            for anchor in parser.anchors:
                anchors.append(anchor)

        return anchors

    @staticmethod
    def _isdir(link: Anchor):
        return link.href.endswith("/")

    @staticmethod
    def _should_ignore(base_url, current_path, link: Anchor):

        if urljoin(base_url, link.href) == urljoin(urljoin(base_url, current_path), "../"):
            return True

        if link.href.endswith(HttpDirectory.BLACK_LIST):
            return True

        # Ignore external links
        full_url = urljoin(base_url, link.href)
        if not full_url.startswith(base_url):
            return True

        # Ignore parameters in url
        if "?" in link.href:
            return True

    def close(self):
        self.session.close()
        logger.debug("Closing HTTPRemoteDirectory for " + self.base_url)


