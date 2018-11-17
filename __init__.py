import logging
from logging import FileHandler, StreamHandler

import sys

logger = logging.getLogger("default")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
file_handler = FileHandler("oddb.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(StreamHandler(sys.stdout))

