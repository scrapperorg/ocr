'''AI analysis worker'''
import os
import logging
from typing import Any, Dict
import requests
import json
import time
import sys

from app.config import (API_ENDPOINT,
                        APP_VERSION,
                        DUMP_JSON,
                        MAX_NUM_PAGES,
                        MIN_QUALITY,
                        OUTPUT_PATH,
                        SLEEP_TIME,
                        WORKER_ID)

from app.constants import (APIStatus,
                           ResponseField,)

from app.services import (doc_analysis,
                          ocr_evaluation,
                          ocr_service,
                          summarization,)
from app.utils.file_util import make_derived_file_name
from tenacity import before_log, retry, stop_after_attempt


logger = logging.getLogger(__name__)

# hack because subprocess does not inherit PATH env variable from virtual env
# on newer python versions
os.environ["PATH"] = os.path.dirname(sys.executable) + ":" + os.environ["PATH"]


def assert_path_exists(path: str) -> None:
    """Asserts that a path exists."""
    if not os.path.exists(path):
        raise ValueError(f"File path {path} does not exist.")


def safe_make_dirs(directory: str) -> None:
    """Utility function to make a directory if it does not exist."""
    if not os.path.exists(directory):
        logger.info(f"Making directory {directory}")
        os.makedirs(directory)


def raise_for_status(response: requests.Response) -> None:
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


@retry(stop=stop_after_attempt(3), before=before_log(logger, logging.INFO))
def get_next_document(not_found: bool = False) -> Dict[Any, Any]:
    """Gets the next document to process from the API."""
    endpoint = os.path.join(API_ENDPOINT, "next-document")
    if not_found:
        endpoint = endpoint + "?forceStatus=not_found"
    response = requests.get(endpoint)
    raise_for_status(response)
    logger.debug(
        f"Endpoint {endpoint} response {response.text} status {response.status_code}"
    )
    parsed_response = response.json()
    return parsed_response


@retry(stop=stop_after_attempt(3), before=before_log(logger, logging.INFO))
def get_document(id: str) -> Dict[Any, Any]:
    """Gets a document by id to process from the API."""
    endpoint = os.path.join(API_ENDPOINT, "document", id)
    logger.info(f"Calling endpoint {endpoint}")
    response = requests.get(endpoint)
    logger.info(f"Endpoint response {response.text}")
    response.raise_for_status()
    return response.json()


def shorten_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Shortens the analysis field of the response."""
    analysis[ResponseField.TEXT] = summarization.summarize(analysis[ResponseField.TEXT])
    return analysis


def shorten_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """Shortens the analysis field of the response."""
    analysis = body.get(ResponseField.ANALYSIS, {})
    if analysis:
        body[ResponseField.ANALYSIS] = shorten_analysis(analysis)
    return body


# @retry(stop=stop_after_attempt(3), before=before_log(logger, logging.INFO))
def update_document(id, status, message="", analysis={}, raise_failure=True):
    """Updates the status of a document in the API.

    :param id: document id
    :param status: status to update
    :param message: additional message containing errors, defaults to ""
    :param analysis: analysis of the document, defaults to {}
    :param raise_failure: raises an exception if API can't process the request\
        defaults to True
    """
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {
        ResponseField.WORKER: WORKER_ID,
        "id": id,
        "status": status,
        "message": message,
        "analysis": analysis,
    }
    stats = analysis.get(ResponseField.STATISTICS, {})
    logger.info(
        f"Calling endpoint {endpoint}"
        f" Document: '{id}' status: '{status}' message: '{message}' stats: '{stats}'"
    )
    response = requests.post(endpoint, json=body)
    logger.info(f"Endpoint response {response.text} status {response.status_code}")
    if response.status_code >= 400:
        logger.info("Trying again with shorter payload")
        response = requests.post(endpoint, json=shorten_payload(body))
        logger.info(f"Endpoint response {response.text} status {response.status_code}")
    if raise_failure:
        raise_for_status(response)


def assert_doc_length(doc_path: str):
    """Asserts that a document is not too long."""
    doc_length = ocr_service.count_pages(doc_path)
    if doc_length > MAX_NUM_PAGES:
        raise ValueError(
            f"Document {doc_path} is too long ({doc_length} pages), max length is {MAX_NUM_PAGES} pages."
        )


def validate_document(document: Dict[str, Any]):
    """Validates that a document is valid for processing."""
    doc_path = document["storagePath"]
    assert_path_exists(doc_path)
    assert ocr_service.is_pdf_valid(doc_path)
    assert_doc_length(doc_path)
    if ocr_service.is_pdf_encrypted(doc_path):
        logger.info(
            f"{doc_path} is encrypted, digitially signed or password protected; atempting to clean..."
        )
        ocr_service.remove_encryption(doc_path)


def process(document: Dict[str, Any],
            output_path: str,
            dump_text: bool = False,
            dump_json: bool = False) -> Dict[str, Any]:
    """Processes a document receieved from the API.

    :param document: document to process
    :param output_path: location to store the output
    :param dump_text: flag to dump the text content to a file, defaults to False
    :param dump_json: flag to dump the json contne to a file, defaults to False
    :return: analysis of the document
    """
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
        logger.info(f"Quality of {ocr_output} is too low. Forcing page rotation and doing again...")
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


def dump_json_to_path(analysis: Dict[str, Any], json_output: str):
    """Dump the analysis to a json file.

    :param analysis: result of the analysis
    :param json_output: location to store the json file
    """
    with open(json_output, "w") as f:
        stats = {
            k: analysis[k]
            for k in analysis.keys()
            if k not in {ResponseField.TEXT}  # ResponseField.ANALYSIS_META}
        }
        json.dump(stats, f, indent=4)


def init():
    """Initializes the worker."""
    safe_make_dirs(OUTPUT_PATH)
    assert_path_exists(OUTPUT_PATH)


def main():
    """Main function of the worker."""
    init()
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
                    logger.info(
                        f"Next document status is {input_status}. Assuming no more documents to process."
                        f" Polling every {SLEEP_TIME} seconds."
                        f"\nThis message will only be logged once."
                    )
                time.sleep(SLEEP_TIME)
            elif input_status in APIStatus.DOWNLOADED:
                logger.info(f"Got document {document}")
                update_document(job_id, APIStatus.LOCKED, message="Processing...")
                validate_document(document)
                update_document(
                    job_id, APIStatus.OCR_INPROGRESS, message="Doing AI analysis..."
                )
                analysis = process(document, OUTPUT_PATH, dump_text=True, dump_json=DUMP_JSON)
                logger.info(
                    f"Processing time took: {analysis[ResponseField.TIME]} seconds {analysis[ResponseField.STATISTICS]}"
                )
                update_document(job_id, APIStatus.OCR_DONE, analysis=analysis)
            elif input_status in {
                APIStatus.OCR_DONE,
                APIStatus.OCR_INPROGRESS,
                APIStatus.LOCKED,
            }:
                message = f"Status of '{job_id}'' is '{input_status}'. Sleeping for {SLEEP_TIME} seconds..."
                logger.info(message)
                update_document(job_id, APIStatus.FAILED, message=message)
                time.sleep(SLEEP_TIME)
            else:
                if input_status != last_input_status:
                    logger.info(
                        f"Status of '{job_id}' is '{input_status}' (unkown). Assuming no more documents to process."
                        f" Expected one of these statuses {APIStatus.statuses()}"
                        f" Next call will take place in {6*SLEEP_TIME} seconds..."
                    )
                time.sleep(SLEEP_TIME)
        except Exception as e:
            message = f"Something went wrong for job id '{job_id}'. "
            logger.exception(message)
            message += str(e)
            if job_id:
                update_document(
                    job_id, APIStatus.FAILED, message=message, raise_failure=False, analysis=analysis
                )
            time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
