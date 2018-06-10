import json
from twisted.protocols.ftp import FTPFileListProtocol
from scrapy.http import Response
from scrapy.core.downloader.handlers.ftp import FTPDownloadHandler


# Inspired by https://github.com/laserson/ftptree
class FtpListingHandler(FTPDownloadHandler):

    def gotClient(self, client, request, file_path):

        protocol = FTPFileListProtocol()

        return client.list(file_path, protocol).addCallbacks(
            callback=self._build_response,
            callbackArgs=(request, protocol),
            errback=self._failed,
            errbackArgs=(request, ))

    def _build_response(self, result, request, protocol):

        self.result = result
        body = json.dumps(protocol.files).encode()
        return Response(url=request.url, status=200, body=body)
