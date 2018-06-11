#! /usr/bin/env python

from threading import Thread
from queue import Queue
import os
import time
import ftputil
import random


class File:

    def __init__(self, name: str, size: int, mtime: str, path: str, is_dir: bool):
        self.name = name
        self.size = size
        self.mtime = mtime
        self.path = path
        self.is_dir = is_dir

    def __str__(self):
        return ("DIR " if self.is_dir else "FILE ") + self.path + "/" + self.name


class FTPConnection(object):
    def __init__(self, host):
        self.host = host
        self.failed_attempts = 0
        self.max_attempts = 5
        self.stop_when_connected()
        self._list_fn = None

    def _connect(self):
        # attempt an anonymous FTP connection
        print("CONNECT %s ATTEMPT", self.host)
        self.ftp = ftputil.FTPHost(self.host, "anonymous", "od-database")
        print("CONNECT %s SUCCESS", self.host)

    def stop_when_connected(self):
        # continually tries to reconnect ad infinitum
        # TODO: Max retries
        try:
            self._connect()
        except Exception:
            print("CONNECT %s FAILED; trying again...", self.host)
            time.sleep(5 * random.uniform(0.5, 1.5))
            self.stop_when_connected()

    def list(self, path) -> list:
        results = []
        self.ftp.chdir(path)
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

        return results

    def process_path(self, path):
        while self.failed_attempts < self.max_attempts:
            try:
                results = self.list(path)
                self.failed_attempts = 0
                return results
            except Exception as e:
                print(e)
                self.failed_attempts += 1
                self.ftp.close()
                print("LIST FAILED; reconnecting...")
                time.sleep(2 * random.uniform(0.5, 1.5))
                self.stop_when_connected()

        # if I get here, I never succeeded in getting the data
        print("LIST ABANDONED %s", path)
        self.failed_attempts = 0
        return []


def process_and_queue(host, q: Queue):

    ftp = FTPConnection(host)

    while True:
        file = q.get()

        if file.is_dir:
            print(file)
            listing = ftp.process_path(os.path.join(file.path, file.name))
            for f in listing:
                q.put(f)
        else:
            pass

        q.task_done()


def do_the_thing():

    host = "80.252.155.68"
    ftp = FTPConnection(host)
    root_listing = ftp.process_path("/")
    ftp.ftp.close()

    q = Queue(maxsize=0)
    num_threads = 10

    for i in range(num_threads):
        worker = Thread(target=process_and_queue, args=(host, q,))
        worker.setDaemon(True)
        worker.start()

    for file in root_listing:
        q.put(file)

    q.join()


if __name__ == '__main__':
    do_the_thing()
