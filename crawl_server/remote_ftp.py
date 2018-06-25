#! /usr/bin/env python
from crawl_server import logger
from urllib.parse import urlparse
import os
import time
import ftputil
import ftputil.error
from ftputil.session import session_factory
from crawl_server.crawler import RemoteDirectory, File, TooManyConnectionsError


class FtpDirectory(RemoteDirectory):

    SCHEMES = ("ftp", )

    CANCEL_LISTING_CODE = (
        550,  # Forbidden
    )

    def __init__(self, url):

        host = urlparse(url).netloc
        super().__init__(host)
        self.max_attempts = 3
        self.ftp = None
        self.stop_when_connected()

    def _connect(self):
        self.ftp = ftputil.FTPHost(self.base_url, "anonymous", "od-database", session_factory=session_factory(
            use_passive_mode=True
        ))
        self.ftp._session.timeout = 30

    def stop_when_connected(self):
        failed_attempts = 0
        while failed_attempts < self.max_attempts:
            try:
                self._connect()
                logger.debug("New FTP connection @ " + self.base_url)
                return True
            except ftputil.error.FTPError as e:

                if e.errno == 530 or e.errno == 421:
                    break

                failed_attempts += 1
                print("Connection error; reconnecting..." + e.strerror + " " + str(e.errno))
                time.sleep(2)
        return False

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
                        file_path = os.path.join(path, file_name)
                        stat = self.try_stat(file_path)
                        is_dir = self.ftp.path.isdir(file_path)

                        results.append(File(
                            name=os.path.join(file_name, "") if is_dir else file_name,
                            mtime=stat.st_mtime,
                            size=-1 if is_dir else stat.st_size,
                            is_dir=is_dir,
                            path=path.strip("/") if not is_dir else path
                        ))
                return path, results
            except ftputil.error.ParserError as e:
                logger.error("TODO: fix parsing error: " + e.strerror + " @ " + str(e.file_name))
                break
            except ftputil.error.FTPError as e:
                if e.errno in FtpDirectory.CANCEL_LISTING_CODE:
                    break
                failed_attempts += 1
                self.reconnect()
            except ftputil.error.PermanentError as e:
                if e.errno == 530:
                    raise TooManyConnectionsError()
                if e.errno is None:
                    failed_attempts += 1
                    self.reconnect()
                else:
                    print(str(e.strerror) + " errno:" + str(e.errno))
                    break
            except Exception as e:
                failed_attempts += 1
                self.reconnect()
                logger.error("Exception while processing FTP listing for " + self.base_url + ": " + str(e))

        return path, []

    def reconnect(self):
        if self.ftp:
            self.ftp.close()
            success = self.stop_when_connected()
            logger.debug("Reconnecting to FTP server " + self.base_url + (" (OK)" if success else " (ERR)"))

    def try_stat(self, path):

        try:
            return self.ftp.stat(path)
        except ftputil.error.ParserError as e:
            # TODO: Try to parse it ourselves?
            logger.error("Exception while parsing FTP listing for " + self.base_url + path + " " + e.strerror)
            return None

    def close(self):
        if self.ftp:
            self.ftp.close()
            self.ftp = None
        logger.debug("Closing FtpRemoteDirectory for " + self.base_url)

