import os
import logging
import pytest
from ocr_worker import (process,
                        validate_document,
                        get_next_document_mock,
                        safe_make_dirs, )

DOC_DIR = 'nlp/documents/'

logging.basicConfig(level="DEBUG")
LOGGER = logging.getLogger(__name__)


def list_docs(dir):
    for fis_name in os.listdir(dir):
        if '.pdf' in fis_name:
            yield fis_name

"""
def test_process_entire_dir():
    for fis_name in list_docs(DOC_DIR):
        doc_id, _ = os.path.splitext(os.path.basename(fis_name))
        output_dir = os.path.join(DOC_DIR, doc_id)
        safe_make_dirs(output_dir)
        document = get_next_document_mock(doc_id, DOC_DIR)
        try:
            validate_document(document)
            analysis = process(document, output_dir)
            dump_json(analysis, output_dir)
        except Exception as e:
            LOGGER.info(F'Eșuat {document}', str(e))
"""

def pipeline(fis_name):
    doc_id, _ = os.path.splitext(os.path.basename(fis_name))
    output_dir = os.path.join(DOC_DIR, doc_id)
    safe_make_dirs(output_dir)
    document = get_next_document_mock(doc_id, DOC_DIR)
    validate_document(document)
    analysis = process(document, output_dir, dump_text=True, dump_json=True)
    return analysis


def test_normal_pdf():
    analysis = pipeline('normal.pdf')
    LOGGER.info(analysis['statistics'])


def test_naturally_occuring_kwds_pdf():
    analysis = pipeline('kwds.pdf')
    LOGGER.info(analysis['statistics'])


def test_keywords_list_pdf():
    analysis = pipeline('keywords.pdf')
    assert analysis['statistics']['num_kwds'] == 365
    LOGGER.info(analysis['statistics'])


def test_empty_pdf():
    with pytest.raises(Exception):
        pipeline("empty.pdf")


def test_typos_pdf():
    analysis = pipeline("typos.pdf")
    print(1)

def test_strange_pdf(caplog):
    caplog.set_level(logging.INFO)
    analysis = pipeline("strange_error.pdf")
    assert len(analysis['text']) > 10
    assert 'The generated PDF is INVALID' in caplog.text


def test_rotated_pdf():
    analysis = pipeline("rotated.pdf")  # "rotated.pdf")
    assert analysis['ocr_quality'] > 90


def test_heavily_rotated_pdf(caplog):
    analysis = pipeline("heavily_rotated.pdf")  # "rotated.pdf")
    assert analysis['ocr_quality'] > 90
    assert "Forcing page rotation" in caplog.text


def test_digitally_signed_pdf():
    analysis = pipeline("digitally_signed.pdf")
    assert len(analysis['text']) > 100


def test_password_encrypted_pdf():
    with pytest.raises(Exception):
        pipeline("password_encrypted.pdf")
