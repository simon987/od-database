#! /usr/bin/env python

from urllib.parse import urlparse
import os
import time
import ftputil
import ftputil.error
from ftputil.session import session_factory
import random
from crawl_server.crawler import RemoteDirectory, File, TooManyConnectionsError


class FtpDirectory(RemoteDirectory):

    SCHEMES = ("ftp", )

    def __init__(self, url):

        host = urlparse(url).netloc
        super().__init__(host)
        self.max_attempts = 3
        self.ftp = None
        self.stop_when_connected()

    def _connect(self):
        self.ftp = ftputil.FTPHost(self.base_url, "anonymous", "od-database", session_factory=session_factory(
            use_passive_mode=False
        ))
        self.ftp._session.timeout = 40

    def stop_when_connected(self):
        failed_attempts = 0
        while failed_attempts < self.max_attempts:
            try:
                self._connect()
                break
            except ftputil.error.FTPError as e:

                if e.errno == 530 or e.errno == 421:
                    print("Cancel connection - too many connections")
                    break

                failed_attempts += 1
                print("Connection error; reconnecting..." + e.strerror + " " + str(e.errno))
                time.sleep(2 * random.uniform(0.5, 1.5))

    def list_dir(self, path):
        if not self.ftp:
            # No connection - assuming that connection was dropped because too many
            raise TooManyConnectionsError()
        results = []
        failed_attempts = 0
        while failed_attempts < self.max_attempts:
            try:
                file_names = self.ftp.listdir(path)

                for file_name in file_names:
                        stat = self.try_stat(os.path.join(path, file_name))
                        is_dir = self.ftp.path.isdir(os.path.join(path, file_name))

                        results.append(File(
                            name=file_name,
                            mtime=stat.st_mtime,
                            size=-1 if is_dir else stat.st_size,
                            is_dir=is_dir,
                            path=path
                        ))
                return path, results
            except ftputil.error.ParserError as e:
                print("TODO: fix parsing error: " + e.strerror + " @ " + str(e.file_name))
                break
            except ftputil.error.FTPOSError as e:
                if e.strerror == "timed out":
                    failed_attempts += 1
                    continue
            except ftputil.error.FTPError as e:
                if e.errno == 530:
                    raise TooManyConnectionsError()
            except Exception as e:
                # TODO remove that debug info
                print("ERROR:" + str(e))
                print(type(e))
                raise e

        return path, []

    def try_stat(self, path):

        try:
            return self.ftp.stat(path)
        except ftputil.error.ParserError as e:
            # TODO: Try to parse it ourselves?
            print("Could not parse " + path + " " + e.strerror)
            return None

    def close(self):
        if self.ftp:
            self.ftp.close()
            self.ftp = None

