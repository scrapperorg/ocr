import os
from ocr_worker import process, get_next_document_mock, safe_make_dirs, dump_json

DOC_DIR = 'nlp/documents/'

def list_docs(dir):
    for fis_name in os.listdir(dir):
        if '.pdf' in fis_name:
            yield fis_name


def test_process_entire_dir():
    for fis_name in list_docs(DOC_DIR):
        doc_id, _ = os.path.splitext(os.path.basename(fis_name))
        output_dir = os.path.join(DOC_DIR, doc_id)
        safe_make_dirs(output_dir)
        document = get_next_document_mock(doc_id, DOC_DIR)
        try:
            analysis = process(document, output_dir)
            dump_json(analysis, output_dir)
        except Exception as e:
            print('eșuat', str(e))
