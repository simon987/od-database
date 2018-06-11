from urllib.parse import urlparse, urljoin, unquote

import os
from lxml import etree
from itertools import repeat
from crawler.crawler import RemoteDirectory, File
import requests
from requests.exceptions import RequestException
from multiprocessing.pool import ThreadPool


class HttpDirectory(RemoteDirectory):

    SCHEMES = ("http", "https",)
    HEADERS = {}
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

    def __init__(self, url):
        super().__init__(url)
        self.parser = etree.HTMLParser(collect_ids=False)

    def list_dir(self, path) -> list:

        results = []

        path_url = urljoin(self.base_url, path)
        body = self._fetch_body(path_url)
        links = self._parse_links(body)

        urls_to_request = []

        for link in links:

            if self._should_ignore(link):
                continue
            file_url = urljoin(path_url, link[1])
            path, file_name = os.path.split(file_url[len(self.base_url) - 1:])

            if self._isdir(link):

                results.append(File(
                    name=file_name,
                    mtime="",
                    size=-1,
                    is_dir=True,
                    path=path
                ))
            else:
                urls_to_request.append(file_url)

        pool = ThreadPool(processes=10)
        files = pool.starmap(HttpDirectory._request_file, zip(repeat(self), urls_to_request))
        for f in files:
            if f:
                results.append(f)

        return results

    def _get_url(self, path: str):
        return urljoin(self.base_url, path)

    @staticmethod
    def _fetch_body(url: str):

        # todo timeout
        print("FETCH " + url)
        r = requests.get(url, headers=HttpDirectory.HEADERS)
        return r.text

    def _parse_links(self, body: str) -> set:

        result = set()
        tree = etree.HTML(body, parser=self.parser)
        links = tree.findall(".//a/[@href]")

        for link in links:
            result.add((link.text, link.get("href")))

        return result

    @staticmethod
    def _isdir(url):
        return url[1].rsplit("?", maxsplit=1)[0].endswith("/")

    def _request_file(self, url):

        # todo timeout
        retries = 3
        while retries > 0:
            try:
                print("HEAD " + url)
                r = requests.head(url, headers=HttpDirectory.HEADERS, allow_redirects=False, timeout=50)

                stripped_url = r.url[len(self.base_url) - 1:]

                path, name = os.path.split(stripped_url)

                return File(
                    path=unquote(path).strip("/"),
                    name=unquote(name),
                    size=int(r.headers["Content-Length"]) if "Content-Length" in r.headers else -1,
                    mtime=r.headers["Date"] if "Date" in r.headers else "?",
                    is_dir=False
                )
            except RequestException:
                retries -= 1

        return None


    @staticmethod
    def _should_ignore(link):
        return link[0] == "../" or link[1].endswith(HttpDirectory.BLACK_LIST)

