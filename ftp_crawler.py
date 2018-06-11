#! /usr/bin/env python

from threading import Thread
from queue import Queue
import os
import time
import ftputil
import ftputil.error
import random


class File:

    def __init__(self, name: str, size: int, mtime: str, path: str, is_dir: bool):
        self.name = name
        self.size = size
        self.mtime = mtime
        self.path = path
        self.is_dir = is_dir
        self.ftp = None

    def __str__(self):
        return ("DIR " if self.is_dir else "FILE ") + self.path + "/" + self.name


class FTPConnection(object):
    def __init__(self, host):
        self.host = host
        self.failed_attempts = 0
        self.max_attempts = 2
        self.ftp = None
        self.stop_when_connected()

    def _connect(self):
        print("Connecting to " + self.host)
        self.ftp = ftputil.FTPHost(self.host, "anonymous", "od-database")

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
                print("LIST FAILED; reconnecting...")
                time.sleep(2 * random.uniform(0.5, 1.5))
                self.stop_when_connected()

    def list_dir(self, path) -> list:
        if not self.ftp:
            return []
        results = []
        self.ftp.chdir(path)
        try:
            file_names = self.ftp.listdir(path)

            for file_name in file_names:
                    stat = self.ftp.stat(file_name)
                    is_dir = self.ftp.path.isdir(os.path.join(path, file_name))

                    results.append(File(
                        name=file_name,
                        mtime=stat.st_mtime,
                        size=-1 if is_dir else stat.st_size,
                        is_dir=is_dir,
                        path=path
                    ))
        except ftputil.error.FTPError:
            print("ERROR parsing " + path)

        return results


def process_and_queue(host, q: Queue):

    ftp = FTPConnection(host)

    while ftp.ftp:
        file = q.get()

        if file.is_dir:
            print(file)
            try:
                listing = ftp.list_dir(os.path.join(file.path, file.name))
                for f in listing:
                    q.put(f)
            except ftputil.error.PermanentError as e:
                if e.errno == 530:
                    # Too many connections, retry this dir but kill this thread
                    q.put(file)
                    ftp.ftp.close()
                    print("Dropping connection because too many")
        else:
            pass

        q.task_done()


def crawl_ftp_server(host: str, max_threads: int) -> list:

    ftp = FTPConnection(host)
    root_listing = ftp.list_dir("/")
    if ftp.ftp:
        ftp.ftp.close()

    q = Queue(maxsize=0)
    for i in range(max_threads):
        worker = Thread(target=process_and_queue, args=(host, q,))
        worker.setDaemon(True)
        worker.start()

    for file in root_listing:
        q.put(file)

    q.join()
    return []


if __name__ == '__main__':
    import sys
    crawl_ftp_server(sys.argv[1], 50)
