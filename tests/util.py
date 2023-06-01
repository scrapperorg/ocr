import logging
import json
import os
from app.services import doc_analysis

from ocr_worker import (API_ENDPOINT,
                        WORKER_ID,
                        ResponseField,)

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


def get_next_document_mock(
    doc_id="38f93d44-1e4e-4c37-9df8-879e2b5993c0",
    directory="nlp/documents/",
    keywords_hash="1",
    keywords=None,
):
    if keywords is None:
        keywords = doc_analysis.load_default_file_keywords()
    in_str = """{{
    "id":	"{doc_id}",
    "storagePath":	"{directory}/{doc_id}.pdf",
    "status": "downloaded"
    }}""".format(
        doc_id=doc_id, directory=directory
    )
    retval = json.loads(in_str)
    retval["keywordsHash"] = keywords_hash
    retval["keywords"] = keywords
    return retval


def update_document_mock(id, status, message="", analysis={}, raise_failure=True):
    endpoint = os.path.join(API_ENDPOINT, "ocr-updates")
    body = {
        ResponseField.WORKER: WORKER_ID,
        "id": id,
        "status": status,
        "message": message,
        "analysis": analysis,
    }
    logger.info(f"Calling endpoint {endpoint} with body {body}")
