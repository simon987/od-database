from urllib.parse import urljoin, unquote

import os
from lxml import etree
from itertools import repeat
from crawl_server.crawler import RemoteDirectory, File
import requests
from requests.exceptions import RequestException
from multiprocessing.pool import ThreadPool
import config
from dateutil.parser import parse as parse_date


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
        self.parser = etree.HTMLParser(collect_ids=False, encoding='utf-8')
        self.session = requests.Session()
        self.session.headers = HttpDirectory.HEADERS

    def list_dir(self, path) -> list:
        results = []

        path_url = os.path.join(self.base_url, path.strip("/"), "")
        body, encoding = self._fetch_body(path_url)
        if not body:
            return []
        links = self._parse_links(body, encoding)

        urls_to_request = []

        for link in links:
            if self._should_ignore(self.base_url, link):
                continue

            file_url = urljoin(path_url, link[1])
            path, file_name = os.path.split(file_url[len(self.base_url) - 1:])

            if self._isdir(link):
                results.append(File(
                    name=file_name,
                    mtime=None,
                    size=None,
                    path=path,
                    is_dir=True
                ))
            else:
                urls_to_request.append(file_url)

        results.extend(self.request_files(urls_to_request))

        return results

    def request_files(self, urls_to_request: list) -> list:

        if len(urls_to_request) > 30:
            # Many urls, use multi-threaded solution
            pool = ThreadPool(processes=10)
            files = pool.starmap(HttpDirectory._request_file, zip(repeat(self), urls_to_request))
            pool.close()
            return [f for f in files if f]
        else:
            # Too few urls to create thread pool
            results = []
            for url in urls_to_request:
                file = self._request_file(url)
                if file:
                    results.append(file)

            return results

    def _get_url(self, path: str):
        return urljoin(self.base_url, path)

    def _fetch_body(self, url: str):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = self.session.get(url)
                return r.content, r.encoding
            except RequestException:
                retries -= 1

        return None

    def _parse_links(self, body: bytes, encoding) -> list:

        result = list()
        try:
            tree = etree.HTML(body, parser=self.parser)
            links = []
            try:
                links = tree.findall(".//a/[@href]")
            except AttributeError:
                pass

            for link in links:
                result.append((link.text, link.get("href")))
        except UnicodeDecodeError:
            tree = etree.HTML(body.decode(encoding, errors="ignore").encode("utf-8"), parser=self.parser)
            links = []
            try:
                links = tree.findall(".//a/[@href]")
            except AttributeError:
                pass

            for link in links:
                result.append((link.text, link.get("href")))

        return result

    @staticmethod
    def _isdir(link: tuple):
        return link[1].rsplit("?", maxsplit=1)[0].endswith("/")

    def _request_file(self, url):

        retries = HttpDirectory.MAX_RETRIES
        while retries > 0:
            try:
                r = self.session.head(url, allow_redirects=False, timeout=50)

                stripped_url = url[len(self.base_url) - 1:]

                path, name = os.path.split(stripped_url)
                date = r.headers["Last-Modified"] if "Last-Modified" in r.headers else "1970-01-01"
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
    def _should_ignore(base_url, link: tuple):
        if link[0] == "../" or link[1].endswith(HttpDirectory.BLACK_LIST):
            return True

        # Ignore external links
        if link[1].startswith("http") and not link[1].startswith(base_url):
            return True

    def close(self):
        self.session.close()

