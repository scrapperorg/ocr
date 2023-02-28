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

POST http://3.229.101.152:8081/ocr_updates
Body: { id, status } unde id este id-ul documentului si status este una din valorile astea: 'downloaded', 'locked', 'ocr_in_progress', 'ocr_done'

'''
import os
import logging
import requests
import json
import time
import sys

from app.constants import APIStatus

from app.services import doc_analysis, ocr_evaluation, ocr_service
from app.utils.file_util import make_derived_file_name, read_text_file


from tenacity import before_log, retry, stop_after_attempt


WORKER_ID = os.environ.get("WORKER_ID", 1)
API_URL = os.environ.get("API_URL", "http://3.229.101.152:8081")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "nlp/documents/analysis")
SLEEP_TIME = os.environ.get("SLEEP_TIME", 10)


LOG_CONFIG = f"Worker{WORKER_ID}: " + " [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
logging.basicConfig(level="INFO", format=LOG_CONFIG)
LOGGER = logging.getLogger(__name__)

# hack because subprocess does not inherit PATH env variable from virtual env
# on newer python versions
os.environ['PATH'] = os.path.dirname(sys.executable) + ':' + os.environ['PATH']

# TODO: write to a shared file
SEEN = set()


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
    ANALYSIS = "highligh_file"
    TEXT = "text_file"
    QUALITY = "ocr_quality"



#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_next_document(not_found=False):
    endpoint = os.path.join(API_URL, "next-document")
    if not_found:
        endpoint = endpoint + "?forceStatus=not_found"
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    LOGGER.info(f"Endpoint response {response.text}")
    return response.json()


def get_next_document_mock():
    #"storagePath":	"/opt/storage/3b4d634d-8616-4809-9c68-2e2c923d1e1a.pdf",
    retval = json.loads("""{
    "id":	"3b4d634d-8616-4809-9c68-2e2c923d1e1a",
    "storagePath":	"nlp/documents/3b4d634d-8616-4809-9c68-2e2c923d1e1a.pdf",
    "status":	"downloaded"
    }""")
    return retval

#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def get_document(id: str):
    endpoint = os.path.join(API_URL, "document", id)
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    LOGGER.info(f"Endpoint response {response.text}")
    return response.json()


#@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def update_document(id, status, message=""):
    endpoint = os.path.join(API_URL, "ocr_updates")
    body = {"id": id, "status": status, "message": message}
    LOGGER.info(f"Calling endpoint {endpoint}")
    response = requests.post(endpoint, json=body)
    LOGGER.info(f"Endpoint response {response.text}")


def process(document):
    job_id = document["id"]
    js_content = {ResponseField.WORKER: WORKER_ID,
                  ResponseField.JOB_ID: job_id,
                  ResponseField.IN_STATUS: document['status']}
    input_file = document["storagePath"]
    js_content[ResponseField.IN] = input_file
    assert_path_exists(input_file)
    ocr_output = make_derived_file_name(input_file, new_path=OUTPUT_PATH, new_extension='pdf', new_suffix='ocr')
    txt_output = make_derived_file_name(input_file, new_path=OUTPUT_PATH, new_extension='txt', new_suffix='ocr')
    anl_output = make_derived_file_name(input_file, new_path=OUTPUT_PATH, new_extension='pdf', new_suffix='highlight')
    json_output = make_derived_file_name(input_file, new_path=OUTPUT_PATH, new_extension='json', new_suffix='analysis')
    ocr_service.call_ocr(input_file, ocr_output)
    # TODO: call this instead of the cli 
    # ocr_service.run_ocr(input_file, ocr_output)
    assert_path_exists(ocr_output)
    js_content[ResponseField.OCR] = ocr_output
    ocr_service.extract_ocrized_text(ocr_output, txt_output)
    assert_path_exists(txt_output)
    js_content[ResponseField.TEXT] = txt_output
    js_content[ResponseField.QUALITY] = ocr_evaluation.estimate_quality(read_text_file(txt_output))
    doc_analysis.highlight_keywords(ocr_output, anl_output)
    assert_path_exists(anl_output)
    js_content[ResponseField.ANALYSIS] = anl_output
    with open(json_output, 'w') as fout:
        json.dump(js_content, fout)
    SEEN.add(job_id)
    

if __name__ == '__main__':
    while True:
        try:
            document = get_next_document()
            job_id = document["id"]
            redo = document.get("force", False)
            input_status = document['status']
            if input_status in {APIStatus.DOWNLOADED, APIStatus.OCR_DONE, APIStatus.LOCKED}:
                if input_status in APIStatus.DOWNLOADED or \
                    (input_status in {APIStatus.OCR_DONE, APIStatus.LOCKED} and redo):
                    update_document(job_id, APIStatus.LOCKED, message="Processing...")
                    update_document(job_id, APIStatus.OCR_INPROGRESS, message="Doing OCR...")
                    process(document)
                    update_document(job_id, APIStatus.OCR_DONE)
                else:
                    message = f"Status of {document['id']} is {input_status}. Use 'force: true' in the payload to redo the processing. Sleeping for {SLEEP_TIME} seconds..."
                    LOGGER.info(message)
                    update_document(job_id, input_status, message=message)
                    time.sleep(SLEEP_TIME)
            elif input_status in APIStatus.OCR_INPROGRESS:
                message = f"Status of {document['id']} is {input_status}. Sleeping for {SLEEP_TIME} seconds..."
                LOGGER.info(message)
                update_document(job_id, input_status, message=message)
                time.sleep(SLEEP_TIME)
            else:
                LOGGER.info(f"Unkown status {input_status}, assuming no more documents to process."
                            f"Expected one of these statuses {APIStatus.statuses()}"
                            f" Sleeping for {SLEEP_TIME} seconds...")
                time.sleep(SLEEP_TIME)
        except Exception as e:
            message = "Something went wrong."
            LOGGER.exception(message)
            message += str(e)
            time.sleep(2)
            update_document(job_id, input_status, message=message)
