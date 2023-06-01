
import os
import logging
import pytest
from tests.util import get_next_document_mock
from ocr_worker import (process,
                        validate_document,
                        safe_make_dirs,
                        shorten_analysis)

DOC_DIR = 'nlp/documents/'

logging.basicConfig(level="DEBUG")
LOGGER = logging.getLogger(__name__)


def list_docs(dir):
    for fis_name in os.listdir(dir):
        if '.pdf' in fis_name:
            yield fis_name


def pipeline(fis_name,
             keywords_hash="1",
             keywords=None):
    doc_id, _ = os.path.splitext(os.path.basename(fis_name))
    output_dir = os.path.join(DOC_DIR, doc_id)
    safe_make_dirs(output_dir)
    document = get_next_document_mock(doc_id,
                                      DOC_DIR,
                                      keywords_hash=keywords_hash,
                                      keywords=keywords)
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
    analysis['statistics'] == {'num_pages': 1,
                               'num_ents': 0,
                               'num_kwds': 1,
                               'num_wds': 14,
                               'num_chars': 124}


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


def test_update_keywords_list():
    kwds1 = [{'name': 'centralizatăaa'}]
    analysis = pipeline("typos.pdf", keywords_hash="1", keywords=kwds1)
    assert analysis['highlight_metadata'][0]['total_occs'] == 1
    kwds2 = [{'name': 'achiz1ție'}]
    analysis = pipeline("typos.pdf", keywords_hash="2", keywords=kwds2)
    assert analysis['highlight_metadata'][0]['total_occs'] == 1


def test_shorten_analysis():
    analysis = pipeline('normal.pdf')
    orig_len = len(analysis['text'])
    analysis = shorten_analysis(analysis)
    assert len(analysis['text']) < orig_len
    LOGGER.info(analysis['statistics'])
