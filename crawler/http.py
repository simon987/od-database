from urllib.parse import urljoin, unquote

import os
from lxml import etree
from itertools import repeat
from crawler.crawler import RemoteDirectory, File
import requests
from requests.exceptions import RequestException
from multiprocessing.pool import ThreadPool
import config
from dateutil.parser import parse as parse_date


class Link:

    def __init__(self, text: str, url: str):
        self.text = text
        self.url = url


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
        "?C=S;O=A",
        "?C=D;O=A"
    )
    MAX_RETRIES = 3

    def __init__(self, url):
        super().__init__(url)
        self.parser = etree.HTMLParser(collect_ids=False)

    def list_dir(self, path) -> list:
        results = []

        path_url = os.path.join(self.base_url, path.strip("/"), "")
        body = self._fetch_body(path_url)
        if not body:
            return []
        links = self._parse_links(body)

        urls_to_request = []

        for link in links:

            if self._should_ignore(link):
                continue

            file_url = urljoin(path_url, link.url)
            path, file_name = os.path.split(file_url[len(self.base_url) - 1:])

            if self._isdir(link):
                results.append(File(
                    name=file_name,
                    mtime=0,
                    size=-1,
                    is_dir=True,
                    path=path
                ))
            else:
                urls_to_request.append(file_url)

        results.extend(self.request_files(urls_to_request))

        return results

    def request_files(self, urls_to_request: list) -> list:

        results = []

        if len(urls_to_request) > 3:
            # Many urls, use multi-threaded solution
            pool = ThreadPool(processes=10)
            files = pool.starmap(HttpDirectory._request_file, zip(repeat(self), urls_to_request))
            pool.close()
            for file in files:
                if file:
                    results.append(file)
        else:
            # Too few urls to create thread pool
            for url in urls_to_request:
                file = self._request_file(url)
                if file:
                    results.append(file)

        return results

    def _get_url(self, path: str):
        return urljoin(self.base_url, path)

    @staticmethod
    def _fetch_body(url: str):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = requests.get(url, headers=HttpDirectory.HEADERS)
                return r.text
            except RequestException:
                retries -= 1

        return None

    def _parse_links(self, body: str) -> set:

        result = set()
        tree = etree.HTML(body, parser=self.parser)
        links = tree.findall(".//a/[@href]")

        for link in links:
            result.add(Link(link.text, link.get("href")))

        return result

    @staticmethod
    def _isdir(link: Link):
        return link.url.rsplit("?", maxsplit=1)[0].endswith("/")

    def _request_file(self, url):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = requests.head(url, headers=HttpDirectory.HEADERS, allow_redirects=False, timeout=50)

                stripped_url = url[len(self.base_url) - 1:]

                path, name = os.path.split(stripped_url)
                date = r.headers["Date"] if "Date" in r.headers else "1970-01-01"
                return File(
                    path=unquote(path).strip("/"),
                    name=unquote(name),
                    size=int(r.headers["Content-Length"]) if "Content-Length" in r.headers else -1,
                    mtime=int(parse_date(date).timestamp()),
                    is_dir=False
                )
            except RequestException:
                retries -= 1

        return None

    @staticmethod
    def _should_ignore(link: Link):
        return link.text == "../" or link.url.endswith(HttpDirectory.BLACK_LIST)

