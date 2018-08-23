import pycurl
from io import BytesIO

from crawl_server import logger
from urllib.parse import unquote, urljoin
import os
from html.parser import HTMLParser
from itertools import repeat
from crawl_server.crawler import RemoteDirectory, File
from multiprocessing.pool import ThreadPool
import config
from dateutil.parser import parse as parse_date
from pycurl import Curl
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
    TIMEOUT = 25

    def __init__(self, url):
        super().__init__(url)
        self.curl = None
        self.curl_head = None
        self.init_curl()

    def init_curl(self):

        self.curl = Curl()
        self.curl.setopt(self.curl.SSL_VERIFYPEER, 0)
        self.curl.setopt(self.curl.SSL_VERIFYHOST, 0)
        self.curl.setopt(pycurl.TIMEOUT, HttpDirectory.TIMEOUT)

        self.curl_head = self._curl_handle()

    def _curl_handle(self):

        curl_head = Curl()
        curl_head.setopt(self.curl.SSL_VERIFYPEER, 0)
        curl_head.setopt(self.curl.SSL_VERIFYHOST, 0)
        curl_head.setopt(pycurl.NOBODY, 1)
        curl_head.setopt(pycurl.TIMEOUT, HttpDirectory.TIMEOUT)

        return curl_head


    def list_dir(self, path):

        current_dir_name = path[path.rstrip("/").rfind("/") + 1: -1]
        path_identifier = hashlib.md5(current_dir_name.encode())
        path_url = urljoin(self.base_url, path, "")
        body = self._fetch_body(path_url)
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
            handles = [self._curl_handle() for _ in range(len(urls_to_request))]
            files = pool.starmap(self._request_file, zip(handles, urls_to_request, repeat(self.base_url)))
            pool.close()
            for file in files:
                if file:
                    yield file
        else:
            # Too few urls to create thread pool
            for url in urls_to_request:
                file = self._request_file(self.curl_head, url, self.base_url)
                if file:
                    yield file

    @staticmethod
    def _request_file(curl, url, base_url):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                raw_headers = BytesIO()
                curl.setopt(pycurl.URL, url)
                curl.setopt(pycurl.HEADERFUNCTION, raw_headers.write)
                curl.perform()

                stripped_url = url[len(base_url) - 1:]
                headers = HttpDirectory._parse_dict_header(raw_headers.getvalue().decode("utf-8", errors="ignore"))
                raw_headers.close()

                path, name = os.path.split(stripped_url)
                date = headers.get("Last-Modified", "1970-01-01")
                return File(
                    path=unquote(path).strip("/"),
                    name=unquote(name),
                    size=int(headers.get("Content-Length", -1)),
                    mtime=int(parse_date(date).timestamp()),
                    is_dir=False
                )
            except pycurl.error as e:
                curl.close()
                retries -= 1
                raise e

        logger.debug("TimeoutError - _request_file")
        raise TimeoutError

    def _fetch_body(self, url: str):
        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                content = BytesIO()
                self.curl.setopt(pycurl.URL, url)
                self.curl.setopt(pycurl.WRITEDATA, content)
                self.curl.perform()

                return content.getvalue().decode("utf-8", errors="ignore")
            except pycurl.error as e:
                self.curl.close()
                retries -= 1
                print(e)
                raise e

        logger.debug("TimeoutError - _fetch_body")
        raise TimeoutError

    @staticmethod
    def _parse_links(body):

        parser = HTMLAnchorParser()
        parser.feed(body)
        return parser.anchors

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

    @staticmethod
    def _parse_dict_header(raw):
        headers = dict()
        for line in raw.split("\r\n")[1:]:  # Ignore first 'HTTP/1.0 200 OK' line
            if line:
                k, v = line.split(":", maxsplit=1)
                headers[k.strip()] = v.strip()

        return headers

    def close(self):
        self.curl.close()
        logger.debug("Closing HTTPRemoteDirectory for " + self.base_url)
        self.init_curl()


