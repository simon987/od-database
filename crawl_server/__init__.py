import logging
from logging import FileHandler

logger = logging.getLogger("default")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
file_handler = FileHandler("crawl_server.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
