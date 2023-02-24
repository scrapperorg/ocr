import asyncio
import logging
from subprocess import run

import fitz

LOGGER = logging.getLogger(__name__)

CMD_ARGS = ["-v", "--skip-text", "-l", "ron"]
# some PDF files might not be convertible to PDF/A
# then we try again with --output-type pdf
FAIL_SAFE_ARGS = ["--output-type", "pdf"]
OCRMYPDF = "ocrmypdf"


def call_ocr(in_file, pdf_output):
    ocrmypdf_args = [OCRMYPDF, *CMD_ARGS, in_file, pdf_output]
    proc = run(ocrmypdf_args, capture_output=True, encoding="utf-8")
    if proc.returncode != 0:
        LOGGER.info("OCR failed, trying again with --output-type pdf")
        ocrmypdf_args = [OCRMYPDF, *FAIL_SAFE_ARGS, *CMD_ARGS, in_file, pdf_output]
        proc = run(ocrmypdf_args, capture_output=True, encoding="utf-8")
        if proc.returncode != 0:
            LOGGER.error(proc.stderr)
            raise Exception(proc.stderr)
    LOGGER.debug(proc.stdout)
    LOGGER.debug(proc.stderr)
    return proc.stdout, proc.stderr


def extract_ocrized_text(pdf_file, txt_output_file):
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for p in pdf_f.pages():
            text += p.get_text()
    with open(txt_output_file, "w", encoding="utf-8") as txt_f:
        txt_f.write(text)
