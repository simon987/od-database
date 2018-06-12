#! /usr/bin/env python

from urllib.parse import urlparse
import os
import time
import ftputil
import ftputil.error
from ftputil.session import session_factory
import random
import timeout_decorator
from crawler.crawler import RemoteDirectory, File, TooManyConnectionsError


class FtpDirectory(RemoteDirectory):

    SCHEMES = ("ftp", )

    def __init__(self, url):
        host = urlparse(url).netloc
        super().__init__(host)
        self.failed_attempts = 0
        self.max_attempts = 2
        self.ftp = None
        self.stop_when_connected()

    def _connect(self):
        self.ftp = ftputil.FTPHost(self.base_url, "anonymous", "od-database", session_factory=session_factory(
            use_passive_mode=False
        ))

    def stop_when_connected(self):
        while self.failed_attempts < self.max_attempts:
            try:
                self._connect()
                self.failed_attempts = 0
                break
            except ftputil.error.FTPError as e:

                if e.errno == 530:
                    print("Cancel connection - too many connections")
                    break

                self.failed_attempts += 1
                print("Connection error; reconnecting...")
                time.sleep(2 * random.uniform(0.5, 1.5))
                self.stop_when_connected()

    @timeout_decorator.timeout(15, use_signals=False)
    def list_dir(self, path) -> list:
        if not self.ftp:
            print("Conn closed")
            return []
        results = []
        try:
            self.ftp.chdir(path)
            file_names = self.ftp.listdir(path)

            for file_name in file_names:
                    stat = self.ftp.stat(file_name)
                    is_dir = self.ftp.path.isdir(os.path.join(path, file_name))

                    results.append(File(
                        name=file_name,
                        mtime=stat.st_mtime,  # TODO: check
                        size=-1 if is_dir else stat.st_size,
                        is_dir=is_dir,
                        path=path
                    ))
        except ftputil.error.FTPError as e:
            if e.errno == 530:
                raise TooManyConnectionsError()
            pass

        return results

    def close(self):
        if self.ftp:
            self.ftp.close()

