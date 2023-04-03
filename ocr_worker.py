'''
GET http://3.229.101.152:8081/next-document
Este folosit sa returneze urmatorul document pentru procesare. Optional poate primi query param forceStatus=not_found ca sa simuleze situatia cand nu mai e nici un fisier de procesat
retval = json.loads("""{
    "id":	"3b4d634d-8616-4809-9c68-2e2c923d1e1a",
    "storagePath":	"/opt/storage/3b4d634d-8616-4809-9c68-2e2c923d1e1a.pdf",
    "status":	"downloaded",
    "force": True
}""")

GET http://3.229.101.152:8081/document/3b4d634d-8616-4809-9c68-2e2c923d1e1a
Returneaza aceleasi info ca next-document doar ca aici sunt cerute specifice pentru un document, folositor daca vrei sa citesti status-ul curent la un momentdat

POST http://3.229.101.152:8081/ocr-updates
Body: { id, status } unde id este id-ul documentului si status este una din valorile astea: 'downloaded', 'locked', 'ocr_in_progress', 'ocr_done'

'''
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

LOG_CONFIG = f"Worker {WORKER_ID}: " + " [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
logging.basicConfig(level="INFO", format=LOG_CONFIG)
LOGGER = logging.getLogger(__name__)

# hack because subprocess does not inherit PATH env variable from virtual env
# on newer python versions
os.environ['PATH'] = os.path.dirname(sys.executable) + ':' + os.environ['PATH']


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
    IN_STATUS = 'input_status'
    OUT = "analysis_file"
    OCR = "ocr_file"
    ANALYSIS = "highlight_file"
    ANALYSIS_META = "highlight_metadata"
    TEXT_FILE = "text_file"
    TEXT = "text"
    QUALITY = "ocr_quality"
    STATISTICS = "statistics"
    TIME = "processing_time"




#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_next_document(not_found=False):
    endpoint = os.path.join(API_ENDPOINT, "next-document")
    if not_found:
        endpoint = endpoint + "?forceStatus=not_found"
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    LOGGER.info(f"Endpoint response {response.text}")
    return response.json()


def get_next_document_mock(doc_id='3b4d634d-8616-4809-9c68-2e2c923d1e1a', directory='nlp/documents/'):
    #doc_id = 'fe1b2d8d-7d89-4af2-aa3e-932d9624f7fb'
    #doc_id = 'encrypt'
    #doc_id = 'empty'
    in_str = """{{
    "id":	"{doc_id}",
    "storagePath":	"{directory}/{doc_id}.pdf",
    "status":	"downloaded"
    }}""".format(doc_id=doc_id, directory=directory)
    retval = json.loads(in_str)
    return retval


#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_document(id: str):
    endpoint = os.path.join(API_ENDPOINT, "document", id)
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    LOGGER.info(f"Endpoint response {response.text}")
    response.raise_for_status()
    return response.json()


#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def update_document(id, status, message="", analysis={}, raise_failure=True):
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {ResponseField.WORKER: WORKER_ID,
            "id": id,
            "status": status,
            "message": message,
            "analysis": analysis
           }
    LOGGER.info(f"Calling endpoint {endpoint}"
                " Document: '{id}' status: '{status}' message: '{message}'")
    response = requests.post(endpoint, json=body)
    LOGGER.info(f"Endpoint response {response.text}")
    if raise_failure:
        response.raise_for_status()


def update_document_mock(id, status, message="", analysis={}, raise_failure=True):
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {ResponseField.WORKER: WORKER_ID,
            "id": id,
            "status": status,
            "message": message,
            "analysis": analysis
           }
    LOGGER.info(f"Calling endpoint {endpoint} with body {body}")
    LOGGER.info(f"Raises failure")


def assert_valid_document(document):
    assert_path_exists(document["storagePath"])


def process(document, output_path, dump_text=False):
    start_time = time.time()
    js_content = {ResponseField.IN_STATUS: document['status']}
    input_file = document["storagePath"]
    js_content[ResponseField.IN] = input_file
    assert_path_exists(input_file)
    ocr_output = make_derived_file_name(input_file, new_path=output_path, new_extension='pdf', new_suffix='ocr')
    anl_output = make_derived_file_name(input_file, new_path=output_path, new_extension='pdf', new_suffix='highlight')
    ocr_service.call_ocr(input_file, ocr_output)
    # TODO: call this instead of the cli
    # ocr_service.run_ocr(input_file, ocr_output)
    assert_path_exists(ocr_output)
    js_content[ResponseField.OCR] = ocr_output
    text = ocr_service.get_ocrized_text_from_blocks(ocr_output)
    js_content[ResponseField.TEXT] = text
    if dump_text is True:
        text_file = make_derived_file_name(input_file, new_path=output_path, new_extension='txt', new_suffix='ocr')
        ocr_service.dump_text(text, text_file)
    js_content[ResponseField.QUALITY] = ocr_evaluation.estimate_quality(text)
    highlight_meta_js, statistics = doc_analysis.highlight_keywords(ocr_output, anl_output)
    js_content[ResponseField.STATISTICS] = statistics
    assert_path_exists(anl_output)
    js_content[ResponseField.ANALYSIS] = anl_output
    js_content[ResponseField.ANALYSIS_META] = highlight_meta_js
    time_duration = round(time.time() - start_time, 3)
    js_content[ResponseField.TIME] = time_duration
    return js_content


if MOCK == 'true':
    get_next_document = get_next_document_mock
    update_document = update_document_mock


def dump_json(analysis, output_path):
    json_output = make_derived_file_name(analysis[ResponseField.IN], new_path=output_path, new_extension='json', new_suffix='stats')
    with open(json_output, 'w') as f:
        stats = {k: analysis[k] for k in (ResponseField.IN, ResponseField.OCR, ResponseField.ANALYSIS, ResponseField.TIME, ResponseField.QUALITY, ResponseField.STATISTICS)}
        #stats = analysis
        json.dump(stats, f, indent=4)


if __name__ == '__main__':
    while True:
        job_id = ""
        try:
            document = get_next_document()
            input_status = document['status']
            job_id = document.get("id", "not_found")
            if input_status in APIStatus.NOT_FOUND:
                LOGGER.info(f"Next document status is {input_status}. Assuming no more documents to process."
                            f" Sleeping for {SLEEP_TIME} seconds...")
                time.sleep(SLEEP_TIME)
            elif input_status in APIStatus.DOWNLOADED:
                update_document(job_id, APIStatus.LOCKED, message="Processing...")
                assert_valid_document(document)
                update_document(job_id, APIStatus.OCR_INPROGRESS, message="Doing OCR...")
                analysis = process(document, OUTPUT_PATH)
                LOGGER.info(f'Processing time took: {analysis[ResponseField.TIME]} seconds')
                if DUMP_JSON is True:
                    dump_json(analysis, OUTPUT_PATH)
                update_document(job_id, APIStatus.OCR_DONE, analysis=analysis)
            elif input_status in {APIStatus.OCR_DONE, APIStatus.OCR_INPROGRESS, APIStatus.LOCKED}:
                message = f"Status of '{job_id}'' is '{input_status}'. Sleeping for {SLEEP_TIME} seconds..."
                LOGGER.info(message)
                update_document(job_id, APIStatus.FAILED, message=message)
                time.sleep(SLEEP_TIME)
            else:
                LOGGER.info(f"Status of '{job_id}' is '{input_status}' (unkown). Assuming no more documents to process."
                            f" Expected one of these statuses {APIStatus.statuses()}"
                            f" Sleeping for {SLEEP_TIME} seconds...")
                time.sleep(SLEEP_TIME)
        except Exception as e:
            message = f"Something went wrong for job id '{job_id}'. "
            LOGGER.exception(message)
            message += str(e)
            if job_id:
                update_document(job_id, APIStatus.FAILED, message=message, raise_failure=False)
            time.sleep(SLEEP_TIME)
