import logging
import os
from pathlib import Path
from tempfile import mkdtemp

from fastapi import File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..services import doc_analysis, ocr_evaluation, ocr_service
from ..utils.file_util import make_download_file_path, read_text_file, upload

LOGGER = logging.getLogger(__name__)


async def run_ocr(file: UploadFile = File(...)) -> FileResponse:
    # TODO: Fix async calls

    try:
        work_folder = Path(mkdtemp(prefix="ocrservice.io."))
        # pdf_input = await upload_async(file, work_folder)
        pdf_input = upload(file, work_folder)
        pdf_output = make_download_file_path(pdf_input)
        analyzed_pdf_output = f"{pdf_output}-highlight.pdf"
        txt_output = f"{pdf_output}.txt"
        # await ocr_service.call_ocr_async(pdf_input, pdf_output, txt_output)
        ocr_service.call_ocr(pdf_input, pdf_output, txt_output)
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
