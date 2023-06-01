import logging
import os

# SECTION: General
APP_VERSION = "1.1.0"


# SECTION: OCR worker
WORKER_ID = os.environ.get("WORKER_ID", 1)
API_URL = os.environ.get("API_URL", "http://3.229.101.152:8081")
API_ENDPOINT = os.environ.get("API_ENDPOINT", API_URL)
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "nlp/documents/analysis")
SLEEP_TIME = int(os.environ.get("SLEEP_TIME", 10))
DUMP_JSON = bool(os.environ.get("DUMP_JSON", False))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
MAX_NUM_PAGES = int(os.environ.get("MAX_NUM_PAGES", 75600))
MIN_QUALITY = 77.0

LOG_CONFIG = (
    f"Worker {WORKER_ID} : {APP_VERSION}: "
    + " [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
)
logging.basicConfig(level=LOG_LEVEL, format=LOG_CONFIG)


# SECTION: OCR service
LEGAL_LANG = "ro_legal"
BACK_LANG = "ron"
# number of parallel processes to use for OCR
NUM_PROC = str(os.environ.get("NUM_PROC", 1))
# maximum number of pages to convert to PDF/A
# otherwise output type is PDF
MAX_PAGE_PDF_A = 50


# SECTION: doc analysis
VECTOR_SEARCH = bool(os.environ.get("VECTOR_SEARCH", True))


# SECTION: summarization
SUMMARIZATION_METHOD = "biasedtextrank"
SUMMARY_SENTENCES = int(os.environ.get("SUMMARY_SENTENCES", 5))
SUMMARY_PHRASES = int(os.environ.get("SUMMARY_PHRASES", 15))
