import logging
import os
from pathlib import Path
from tempfile import mkdtemp

import requests
from fastapi import File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from tenacity import before_log, retry, stop_after_attempt

from ..services import doc_analysis, ocr_evaluation, ocr_service
from ..utils.file_util import make_download_file_path, read_text_file, upload

OCR_DONE_WEBHOOK = os.environ.get("OCR_DONE_WEBHOOK", "http://localhost:8081/ocr_done")
LOGGER = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def call_webhook(job_id: str):
    LOGGER.info(f"Calling webhook for {job_id}")
    response = requests.post(OCR_DONE_WEBHOOK, json={"job_id": job_id})
    LOGGER.info(f"Webhook response {response.text}")


def run_ocr(job_id: str, file: UploadFile = File(...)) -> FileResponse:
    try:
        work_folder = Path(mkdtemp(prefix="ocrservice.io."))
        pdf_input = upload(file, work_folder)
        pdf_output = make_download_file_path(pdf_input)
        analyzed_pdf_output = f"{pdf_output}-highlight.pdf"
        txt_output = f"{pdf_output}.txt"
        LOGGER.info(f"Doing OCR for {job_id}")
        ocr_service.call_ocr(pdf_input, pdf_output)
        ocr_service.extract_ocrized_text(pdf_output, txt_output)
        try:
            call_webhook(job_id)
        except Exception as e:
            LOGGER.exception(e)
        return pdf_output, txt_output, analyzed_pdf_output
    except Exception as e:
        LOGGER.exception(e)
        raise HTTPException(
            status_code=400, detail=f"File {file.filename} Error when uploading file."
        )
    finally:
        file.file.close()


def ocr_simple(file: UploadFile = File(...)) -> FileResponse:
    """Perform OCR on the PDF and return the result"""
    try:
        work_folder = Path(mkdtemp(prefix="ocrservice.io."))
        pdf_input = upload(file, work_folder)
        pdf_output = make_download_file_path(pdf_input)
        txt_output = f"{pdf_output}.txt"
        ocr_service.call_ocr(pdf_input, pdf_output, txt_output)
        response = FileResponse(
            path=pdf_output,
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(pdf_output)}"
            },
        )
        return response
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"File {file.filename} Error when uploading file."
        )
    finally:
        file.file.close()


def estimate_quality(txt_file_path: str) -> float:
    """Estimate the quality of the OCR process"""
    return ocr_evaluation.estimate_quality(read_text_file(txt_file_path))


def analyze_pdf(in_pdf_path: str, out_pdf_path: str):
    """Highlight keywords in pdf [under development]"""
    doc_analysis.highlight_keywords(in_pdf_path, out_pdf_path)
