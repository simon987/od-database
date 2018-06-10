import json
import scrapy
import os
from scrapy_od_database.items import File


class AnonFtpRequest(scrapy.Request):

    anon_meta = {
        "ftp_user": "anonymous",
        "ftp_password": "od-database"
    }

    def __init__(self, *args, **kwargs):
        super(AnonFtpRequest, self).__init__(*args, **kwargs)
        self.meta.update(self.anon_meta)


class FtpLinksSpider(scrapy.Spider):
    """Scrapy spider for ftp directories. Will gather all files recursively"""

    name = "ftp_links"

    handle_httpstatus_list = [404]

    def __index__(self, **kw):
        super(FtpLinksSpider, self).__init__(**kw)
        self.base_url = kw.get("base_url")

    def start_requests(self):
        yield AnonFtpRequest(url=self.base_url, callback=self.parse)

    def parse(self, response):
        stripped_url = response.url[len(self.base_url) - 1:]

        files = json.loads(response.body)
        for file in files:

            if file['filetype'] == 'd':
                yield AnonFtpRequest(os.path.join(response.url, file["filename"]))

            if file['filetype'] == '-':
                print(file)
                result = File(
                    name=file['filename'],
                    path=stripped_url.strip("/"),
                    size=file['size'],
                    mtime=file['date'])
                yield result
