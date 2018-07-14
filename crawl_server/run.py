from crawl_server.task_manager import TaskManager
import time
import config

tm = TaskManager(config.CRAWL_SERVER_PROCESSES)

while True:
    time.sleep(1)
