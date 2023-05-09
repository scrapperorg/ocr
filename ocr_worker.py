'''AI analysis worker'''
import os
import logging
import requests
import json
import time
import sys
import time
from app.constants import APIStatus

from app.services import doc_analysis, ocr_evaluation, ocr_service
from app.utils.file_util import make_derived_file_name, read_text_file


from tenacity import before_log, retry, stop_after_attempt

MOCK = os.environ.get("MOCK", False)
WORKER_ID = os.environ.get("WORKER_ID", 1)
API_URL = os.environ.get("API_URL", "http://3.229.101.152:8081")
API_ENDPOINT = os.environ.get("API_ENDPOINT", API_URL)
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "nlp/documents/analysis")
SLEEP_TIME = int(os.environ.get("SLEEP_TIME", 10))
DUMP_JSON = bool(os.environ.get("DUMP_JSON", False))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
MAX_NUM_PAGES = int(os.environ.get("MAX_NUM_PAGES", 75600))
MIN_QUALITY = 77.


APP_VERSION = "1.0.0"

LOG_CONFIG = (
    f"Worker {WORKER_ID} : {APP_VERSION}: "
    + " [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
)
logging.basicConfig(level=LOG_LEVEL, format=LOG_CONFIG)

LOGGER = logging.getLogger(__name__)

# hack because subprocess does not inherit PATH env variable from virtual env
# on newer python versions
os.environ["PATH"] = os.path.dirname(sys.executable) + ":" + os.environ["PATH"]


def assert_path_exists(path):
    if not os.path.exists(path):
        raise ValueError(f"File path {path} does not exist.")


def safe_make_dirs(directory):
    if not os.path.exists(directory):
        LOGGER.info(f"Making directory {directory}")
        os.makedirs(directory)


safe_make_dirs(OUTPUT_PATH)
assert_path_exists(OUTPUT_PATH)


class ResponseField:
    WORKER = "worker_id"
    IN = "input_file"
    JOB_ID = "job_id"
    IN_STATUS = "input_status"
    OUT = "analysis_file"
    OCR = "ocr_file"
    ANALYSIS = "highlight_file"
    ANALYSIS_META = "highlight_metadata"
    TEXT_FILE = "text_file"
    TEXT = "text"
    QUALITY = "ocr_quality"
    STATISTICS = "statistics"
    TIME = "processing_time"
    WK_VERSION = "worker_version"
    KWDS_HASH = 'keywords_hash'


def raise_for_status(response):
    """Raises :class:`HTTPError`, if one occurred."""
    http_error_msg = ""
    if isinstance(response.reason, bytes):
        # We attempt to decode utf-8 first because some servers
        # choose to localize their reason strings. If the string
        # isn't utf-8, we fall back to iso-8859-1 for all other
        # encodings. (See PR #3538)
        try:
            reason = response.reason.decode("utf-8")
        except UnicodeDecodeError:
            reason = response.reason.decode("iso-8859-1")
    else:
        reason = response.reason
    if 500 <= response.status_code < 600:
        http_error_msg = f"{response.status_code} for url: {response.url} Server Error: {reason}: {response.text}"
    if http_error_msg:
        raise requests.HTTPError(http_error_msg, response=response)


# @retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_next_document(not_found=False):
    endpoint = os.path.join(API_ENDPOINT, "next-document")
    if not_found:
        endpoint = endpoint + "?forceStatus=not_found"
    response = requests.get(endpoint)
    raise_for_status(response)
    LOGGER.debug(
        f"Endpoint {endpoint} response {response.text} status {response.status_code}"
    )
    parsed_response = response.json()
    return parsed_response


def get_next_document_mock(
    doc_id="38f93d44-1e4e-4c37-9df8-879e2b5993c0", directory="nlp/documents/"
):
    # doc_id = 'fe1b2d8d-7d89-4af2-aa3e-932d9624f7fb'
    # doc_id = '3b4d634d-8616-4809-9c68-2e2c923d1e1a'
    # doc_id = 'encrypt'
    # doc_id = 'empty'
    # doc_id = "digitally_signed"
    kwds = doc_analysis.load_default_file_keywords()
    in_str = """{{
    "id":	"{doc_id}",
    "storagePath":	"{directory}/{doc_id}.pdf",
    "status": "downloaded"
    }}""".format(
        doc_id=doc_id, directory=directory
    )
    retval = json.loads(in_str)
    retval["keywordsHash"] = "1"
    retval["keywords"] = kwds
    return retval


# @retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_document(id: str):
    endpoint = os.path.join(API_ENDPOINT, "document", id)
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    LOGGER.info(f"Endpoint response {response.text}")
    response.raise_for_status()
    return response.json()


# @retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def update_document(id, status, message="", analysis={}, raise_failure=True):
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {
        ResponseField.WORKER: WORKER_ID,
        "id": id,
        "status": status,
        "message": message,
        "analysis": analysis,
    }
    stats = analysis.get(ResponseField.STATISTICS, {})
    LOGGER.info(
        f"Calling endpoint {endpoint}"
        f" Document: '{id}' status: '{status}' message: '{message}' stats: '{stats}'"
    )
    response = requests.post(endpoint, json=body)
    LOGGER.info(f"Endpoint response {response.text} status {response.status_code}")
    if raise_failure:
        response.raise_for_status()


def update_document_mock(id, status, message="", analysis={}, raise_failure=True):
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {
        ResponseField.WORKER: WORKER_ID,
        "id": id,
        "status": status,
        "message": message,
        "analysis": analysis,
    }
    LOGGER.info(f"Calling endpoint {endpoint} with body {body}")


def assert_doc_length(doc_path):
    doc_length = ocr_service.count_pages(doc_path)
    if doc_length > MAX_NUM_PAGES:
        raise ValueError(
            f"Document {doc_path} is too long ({doc_length} pages), max length is {MAX_NUM_PAGES} pages."
        )


def validate_document(document):
    doc_path = document["storagePath"]
    assert_path_exists(doc_path)
    assert ocr_service.is_pdf_valid(doc_path)
    assert_doc_length(doc_path)
    if ocr_service.is_pdf_encrypted(doc_path):
        LOGGER.info(
            f"{doc_path} is encrypted, digitially signed or password protected; atempting to clean..."
        )
        ocr_service.remove_encryption(doc_path)


def process(document, output_path, dump_text=False, dump_json=False):
    start_time = time.time()
    js_content = {ResponseField.IN_STATUS: document["status"]}
    js_content = {ResponseField.WK_VERSION: APP_VERSION}
    input_file = document["storagePath"]
    js_content[ResponseField.IN] = input_file
    assert_path_exists(input_file)
    ocr_output = make_derived_file_name(
        input_file, new_path=output_path, new_extension="pdf", new_suffix="ocr"
    )
    anl_output = make_derived_file_name(
        input_file, new_path=output_path, new_extension="pdf", new_suffix="highlight"
    )
    ocr_service.call_ocr(input_file, ocr_output, force_rotate=False)
    # TODO: call this instead of the cli
    # ocr_service.run_ocr(input_file, ocr_output)
    assert_path_exists(ocr_output)
    js_content[ResponseField.OCR] = ocr_output
    text = ocr_service.get_ocrized_text_from_blocks(ocr_output)
    js_content[ResponseField.TEXT] = text
    js_content[ResponseField.QUALITY] = ocr_evaluation.estimate_quality(text)
    if js_content[ResponseField.QUALITY] < MIN_QUALITY:
        LOGGER.info(f"Quality of {ocr_output} is too low. Forcing page rotation and doing again...")
        ocr_service.call_ocr(input_file, ocr_output, force_rotate=True)
        assert_path_exists(ocr_output)
        js_content[ResponseField.OCR] = ocr_output
        text = ocr_service.get_ocrized_text_from_blocks(ocr_output)
        js_content[ResponseField.TEXT] = text
        js_content[ResponseField.QUALITY] = ocr_evaluation.estimate_quality(text)

    text_file = 'not_dumped'
    if dump_text is True:
        text_file = make_derived_file_name(
            input_file, new_path=output_path, new_extension="txt", new_suffix="ocr"
        )
        ocr_service.dump_text(text, text_file)
        assert_path_exists(text_file)
    js_content[ResponseField.TEXT_FILE] = text_file
    kwds_hash = document.get('keywordsHash', '0')
    js_content[ResponseField.KWDS_HASH] = kwds_hash
    highlight_meta_js, statistics = doc_analysis.highlight_keywords(
        ocr_output, anl_output, document.get('keywords', []), kwds_hash
    )
    js_content[ResponseField.STATISTICS] = statistics
    assert_path_exists(anl_output)
    js_content[ResponseField.ANALYSIS] = anl_output
    js_content[ResponseField.ANALYSIS_META] = highlight_meta_js
    time_duration = round(time.time() - start_time, 3)
    js_content[ResponseField.TIME] = time_duration
    if dump_json is True:
        json_file = make_derived_file_name(
            input_file, new_path=output_path, new_extension="json", new_suffix="stats"
        )
        dump_json_to_path(js_content, json_file)
        assert_path_exists(json_file)
    return js_content


if MOCK == "true":
    get_next_document = get_next_document_mock
    update_document = update_document_mock


def dump_json_to_path(analysis, json_output):
    with open(json_output, "w") as f:
        stats = {
            k: analysis[k]
            for k in analysis.keys()
            if k not in {ResponseField.TEXT}#, ResponseField.ANALYSIS_META}
        }
        json.dump(stats, f, indent=4)


if __name__ == "__main__":
    input_status = "no_input_status"
    while True:
        job_id = ""
        analysis = {}
        try:
            document = get_next_document()
            last_input_status = input_status
            input_status = document["status"]
            job_id = document.get("id", "not_found")
            if input_status in APIStatus.NOT_FOUND:
                if input_status != last_input_status:
                    LOGGER.info(
                        f"Next document status is {input_status}. Assuming no more documents to process."
                        f" Polling every {SLEEP_TIME} seconds."
                        f"\nThis message will only be logged once."
                    )
                time.sleep(SLEEP_TIME)
            elif input_status in APIStatus.DOWNLOADED:
                LOGGER.info(f"Got document {document}")
                update_document(job_id, APIStatus.LOCKED, message="Processing...")
                validate_document(document)
                update_document(
                    job_id, APIStatus.OCR_INPROGRESS, message="Doing AI analysis..."
                )
                analysis = process(document, OUTPUT_PATH, dump_text=True, dump_json=DUMP_JSON)
                LOGGER.info(
                    f"Processing time took: {analysis[ResponseField.TIME]} seconds {analysis[ResponseField.STATISTICS]}"
                )
                update_document(job_id, APIStatus.OCR_DONE, analysis=analysis)
            elif input_status in {
                APIStatus.OCR_DONE,
                APIStatus.OCR_INPROGRESS,
                APIStatus.LOCKED,
            }:
                message = f"Status of '{job_id}'' is '{input_status}'. Sleeping for {SLEEP_TIME} seconds..."
                LOGGER.info(message)
                update_document(job_id, APIStatus.FAILED, message=message)
                time.sleep(SLEEP_TIME)
            else:
                if input_status != last_input_status:
                    LOGGER.info(
                        f"Status of '{job_id}' is '{input_status}' (unkown). Assuming no more documents to process."
                        f" Expected one of these statuses {APIStatus.statuses()}"
                        f" Next call will take place in {6*SLEEP_TIME} seconds..."
                    )
                time.sleep(SLEEP_TIME)
        except Exception as e:
            message = f"Something went wrong for job id '{job_id}'. "
            LOGGER.exception(message)
            message += str(e)
            if job_id:
                update_document(
                    job_id, APIStatus.FAILED, message=message, raise_failure=False, analysis=analysis
                )
            time.sleep(SLEEP_TIME)
