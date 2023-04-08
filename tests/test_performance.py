import sys
import os
import logging
import json
import numpy as np
from ocr_worker import (process,
                        validate_document,
                        get_next_document_mock,
                        safe_make_dirs,
                        dump_json,
                        APP_VERSION,
                        )


LOGGER = logging.getLogger(__name__)


def files_in_folder(mypath, filter=""):
    return sorted(
        [
            os.path.join(mypath, f)
            for f in os.listdir(mypath)
            if filter in f and os.path.isfile(os.path.join(mypath, f))
        ]
    )


def folders_in_folder(mypath):
    return sorted(
        [
            os.path.join(mypath, f)
            for f in os.listdir(mypath)
            if os.path.isdir(os.path.join(mypath, f))
        ]
    )


def run_performance_test(input_dir, out_dir, analysis_file=f'perf_analysis_default_.jsonl'):
    """Path to downloaded dirs with docs"""
    item = {}
    safe_make_dirs(out_dir)
    out_file = os.path.join(out_dir, analysis_file)
    with open(out_file, "w") as f:
        f.write("")
    for corpus in folders_in_folder(input_dir):
        LOGGER.info(corpus)
        out_corpus = os.path.join(out_dir, os.path.basename(corpus))
        safe_make_dirs(out_corpus)
        for law_dir in folders_in_folder(corpus):
            out_law_dir = os.path.join(out_corpus, os.path.basename(law_dir))
            safe_make_dirs(out_law_dir)
            LOGGER.info(law_dir)
            law = os.path.basename(law_dir)
            for pdf_file in files_in_folder(law_dir, filter=".pdf"):
                LOGGER.info(pdf_file)
                doc_id = os.path.basename(pdf_file).replace(".pdf", "")
                document = get_next_document_mock(doc_id, law_dir)
                try:
                    validate_document(document)
                    analysis = process(document, out_law_dir, dump_text=True)
                    dump_json(analysis, out_law_dir)
                    item["corpus"] = os.path.basename(corpus)
                    item["law"] = law
                    item["doc_id"] = doc_id
                    item["status"] = "ok"
                    item["ocr_quality"] = analysis["ocr_quality"]
                    item["processing_time"] = analysis["processing_time"]
                    item["num_unq_kwds"] = len(analysis["highlight_metadata"])
                    item["avg_number_of_occ"] = np.mean(
                        [len(a["occs"]) for a in analysis["highlight_metadata"]]
                    )
                    item.update(analysis["statistics"])
                except Exception as e:
                    item["corpus"] = os.path.basename(corpus)
                    item["law"] = law
                    item["doc_id"] = doc_id
                    item["status"] = str(e)
                    item["ocr_quality"] = -1
                    item["processing_time"] = -1
                    item["num_unq_kwds"] = -1
                    item["avg_number_of_occ"] = -1
                with open(out_file, "a") as f:
                    f.write(json.dumps(item) + "\n")


def test_performance():
    pass


if __name__ == "__main__":
    run_performance_test(input_dir=sys.argv[1], out_dir=sys.argv[2], analysis_file=f'perf_analysis_{APP_VERSION}_.jsonl')
