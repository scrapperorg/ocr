import logging
import os

WORKER_ID = os.environ.get("WORKER_ID", 1)
LOG_CONFIG = (
    f"Worker {WORKER_ID}: "
    + " [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
)
logging.basicConfig(level="INFO", format=LOG_CONFIG)
