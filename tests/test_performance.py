import sys
import os
import logging
import json
import numpy as np
from ocr_worker import process, get_next_document_mock, safe_make_dirs, dump_json


LOG_CONFIG = f"Perf. test [%(levelname)s] %(asctime)s %(name)s:%(lineno)d - %(message)s"
logging.basicConfig(level="INFO", format=LOG_CONFIG)
LOGGER = logging.getLogger(__name__)


def files_in_folder(mypath, filter=''):
    return sorted([ os.path.join(mypath,f) for f in os.listdir(mypath) if filter in f and os.path.isfile(os.path.join(mypath,f)) ])


def folders_in_folder(mypath):
    return sorted([ os.path.join(mypath,f) for f in os.listdir(mypath) if os.path.isdir(os.path.join(mypath,f)) ])


def run_performance_test(corpus_path, out_file='performance_test.jsonl'):
    """Path to downloaded dirs with docs"""
    item = {}
    with open(out_file, 'w') as f:
        f.write('')
    for corpus in folders_in_folder(corpus_path):
        LOGGER.info(corpus)
        for law_dir in folders_in_folder(corpus):
            analysis_directory = os.path.join(law_dir, 'analysis')
            safe_make_dirs(analysis_directory)
            LOGGER.info(law_dir)
            law = os.path.basename(law_dir)
            for pdf_file in files_in_folder(law_dir, filter='.pdf'):
                LOGGER.info(pdf_file)
                doc_id = os.path.basename(pdf_file).replace('.pdf', '')
                document = get_next_document_mock(doc_id, law_dir)
                try:
                    analysis = process(document, analysis_directory, dump_text=True)
                    dump_json(analysis, law_dir)
                    item['corpus'] = os.path.basename(corpus)
                    item['law'] = law
                    item['doc_id'] = doc_id
                    item['status'] = 'ok'
                    item['ocr_quality'] = analysis['ocr_quality']
                    item['processing_time'] = analysis['processing_time']
                    item['num_unq_kwds'] = len(analysis['highlight_metadata'])
                    item['avg_number_of_occ'] = np.mean([len(a['occs']) for a in analysis['highlight_metadata']])
                    item.update(analysis['statistics'])
                except Exception as e:
                    item['corpus'] = os.path.basename(corpus)
                    item['law'] = law
                    item['doc_id'] = doc_id
                    item['ocr_quality'] = -1
                    item['processing_time'] = -1
                    item['num_unq_kwds'] = -1
                    item['avg_number_of_occ'] = -1
                    item['message'] = str(e)
                with open(out_file, 'a') as f:
                    f.write(json.dumps(item) + '\n')


def test_performance():
    pass


if __name__ == '__main__':
    run_performance_test(sys.argv[1], out_file=sys.argv[2])
