import logging

LOG_CONFIG = "[%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
logging.basicConfig(level="DEBUG", format=LOG_CONFIG)
