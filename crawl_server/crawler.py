import os
import ujson
from urllib.parse import urlparse
from timeout_decorator.timeout_decorator import TimeoutError
from threading import Thread
from queue import Queue, Empty


class TooManyConnectionsError(Exception):
    pass


class File:
    __slots__ = "name", "size", "mtime", "path", "is_dir"

    def __init__(self, name: str, size: int, mtime: int, path: str, is_dir: bool):
        self.name = name
        self.size = size
        self.mtime = mtime
        self.path = path
        self.is_dir = is_dir

    def __bytes__(self):
        return b"|".join([
            self.name.encode(),
            b"D" if self.is_dir else b"F",
            str(self.size).encode(),
            str(self.mtime).encode(),
        ])

    def to_json(self):
        return ujson.dumps({
            "name": self.name,
            "size": self.size,
            "mtime": self.mtime,
            "path": self.path,
        })


class RemoteDirectory:

    SCHEMES = ()

    def __init__(self, base_url):
        self.base_url = base_url

    def list_dir(self, path: str):
        raise NotImplementedError

    def close(self):
        pass


class RemoteDirectoryFactory:

    from crawl_server.remote_ftp import FtpDirectory
    from crawl_server.remote_http import HttpDirectory
    DIR_ENGINES = (FtpDirectory, HttpDirectory)

    @staticmethod
    def get_directory(url) -> RemoteDirectory:

        parsed_url = urlparse(url)

        for dir_engine in RemoteDirectoryFactory.DIR_ENGINES:
            if parsed_url.scheme in dir_engine.SCHEMES:
                return dir_engine(url)


class CrawlResult:

    def __init__(self, file_count: int, status_code: str):
        self.file_count = file_count
        self.status_code = status_code


class RemoteDirectoryCrawler:

    MAX_TIMEOUT_RETRIES = 3

    def __init__(self, url, max_threads: int):
        self.url = url
        self.max_threads = max_threads
        self.crawled_paths = list()

    def crawl_directory(self, out_file: str) -> CrawlResult:
        try:
            try:
                directory = RemoteDirectoryFactory.get_directory(self.url)
                path, root_listing = directory.list_dir("")
                self.crawled_paths.append(path)
                directory.close()
            except TimeoutError:
                return CrawlResult(0, "timeout")

            in_q = Queue(maxsize=0)
            files_q = Queue(maxsize=0)
            for f in root_listing:
                if f.is_dir:
                    in_q.put(os.path.join(f.path, f.name, ""))
                else:
                    files_q.put(f)

            threads = []
            for i in range(self.max_threads):
                worker = Thread(target=RemoteDirectoryCrawler._process_listings, args=(self, self.url, in_q, files_q))
                threads.append(worker)
                worker.start()

            files_written = []  # Pass array to worker to get result
            file_writer_thread = Thread(target=RemoteDirectoryCrawler._log_to_file, args=(files_q, out_file, files_written))
            file_writer_thread.start()

            in_q.join()
            files_q.join()
            print("Done")

            # Kill threads
            for _ in threads:
                in_q.put(None)
            for t in threads:
                t.join()
            files_q.put(None)
            file_writer_thread.join()

            return CrawlResult(files_written[0], "success")
        except Exception as e:
            return CrawlResult(0, str(e) + " \nType:" + str(type(e)))

    def _process_listings(self, url: str, in_q: Queue, files_q: Queue):

        directory = RemoteDirectoryFactory.get_directory(url)
        timeout_retries = RemoteDirectoryCrawler.MAX_TIMEOUT_RETRIES

        while directory:
            try:
                path = in_q.get(timeout=300)
            except Empty:
                directory.close()
                break

            if path is None:
                break

            try:
                path_id, listing = directory.list_dir(path)
                if len(listing) > 0 and path_id not in self.crawled_paths:
                    self.crawled_paths.append(path_id)
                    timeout_retries = RemoteDirectoryCrawler.MAX_TIMEOUT_RETRIES

                    for f in listing:
                        if f.is_dir:
                            in_q.put(os.path.join(f.path, f.name, ""))
                        else:
                            files_q.put(f)
                    import sys
                    print("LISTED " + repr(path) + "dirs:" + str(in_q.qsize()))
                else:
                    pass
                    # print("SKIPPED: " + path + ", dropped " + str(len(listing)))
            except TooManyConnectionsError:
                print("Too many connections")
                # Kill worker and resubmit listing task
                directory.close()
                in_q.put(path)
                break
            except TimeoutError:
                if timeout_retries > 0:
                    timeout_retries -= 1
                    # TODO: Remove debug info
                    print("TIMEOUT, " + str(timeout_retries) + " retries left")
                    in_q.put(path)
                else:
                    print("Dropping listing for " + path)
            finally:
                in_q.task_done()

    @staticmethod
    def _log_to_file(files_q: Queue, out_file: str, files_written: list):

        counter = 0

        with open(out_file, "w") as f:
            while True:

                try:
                    file = files_q.get(timeout=800)
                except Empty:
                    break

                if file is None:
                    break

                f.write(file.to_json() + "\n")
                counter += 1
                files_q.task_done()

        files_written.append(counter)
        print("File writer done")



