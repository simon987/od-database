from crawl_server.task_manager import TaskManager
import time
import config

tm = TaskManager(config.CRAWL_SERVER_PROCESSES)
# TODO: On start, indicate that all tasks assigned to this crawler have been dropped

while True:
    time.sleep(1)
