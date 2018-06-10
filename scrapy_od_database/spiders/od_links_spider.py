import scrapy
import os
from urllib.parse import unquote


class LinksSpider(scrapy.Spider):
    """Scrapy spider for open directories. Will gather all download links recursively"""

    name = "od_links"

    black_list = (
        "?C=N&O=D",
        "?C=M&O=A",
        "?C=S&O=A",
        "?C=D&O=A",
        "?C=N;O=D",
        "?C=M;O=A",
        "?C=S;O=A",
        "?C=D;O=A"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crawled_links = set()

    def __index__(self, **kw):
        super(LinksSpider, self).__init__(**kw)
        self.base_url = kw.get("base_url")

    def should_ask_headers(self, link):
        """Whether or not to send HEAD request"""
        return link not in self.crawled_links and not link.rsplit("?", maxsplit=1)[0].endswith("/")

    def should_crawl(self, link):
        """Whether or not the link should be followed"""
        if link in self.crawled_links:
            return False

        if link.endswith(tuple(self.black_list)):
            return False

        if not link.startswith(self.base_url):
            return False

        return link.rsplit("?", maxsplit=1)[0].endswith("/")

    def start_requests(self):
        yield scrapy.Request(url=self.base_url, callback=self.parse)

    def parse(self, response):
        if response.status == 200:
            links = response.xpath('//a/@href').extract()
            for link in links:
                full_link = response.urljoin(link)

                if self.should_ask_headers(full_link):
                    yield scrapy.Request(full_link, method="HEAD", callback=self.save_file)
                elif self.should_crawl(full_link):
                    self.crawled_links.add(full_link)
                    yield scrapy.Request(full_link, callback=self.parse)

    def save_file(self, response):

        if response.status == 200:
            # Save file information
            stripped_url = response.url[len(self.base_url) - 1:]
            self.crawled_links.add(response.url)

            path, name = os.path.split(stripped_url)

            yield {
                "path": unquote(path).strip("/"),
                "name": unquote(name),
                "size": int(response.headers["Content-Length"].decode("utf-8")) if "Content-Length" in response.headers else -1,
                "mime": response.headers["Content-Type"].decode("utf-8").split(";", maxsplit=1)[0]
                if "Content-Type" in response.headers else "?",
                "mtime": response.headers["Date"].decode("utf-8") if "Date" in response.headers else "?"
            }

