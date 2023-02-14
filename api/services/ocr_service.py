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


def call_ocr(in_file, pdf_output, txt_output):
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


async def call_ocr_async(in_file, pdf_output):
    # sub process is here, and here is where the exception happens.
    # TODO: when --sidecar is provided and the pdf already has text,
    # the cmd skips all pages with text
    cmd_args = CMD_ARGS
    ocrmypdf_args = [OCRMYPDF, *cmd_args, in_file, pdf_output]
    proc = await asyncio.create_subprocess_exec(
        *ocrmypdf_args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        LOGGER.error(stderr)
        raise Exception(stderr)
    LOGGER.debug(stdout.decode())
    LOGGER.debug(stderr.decode())
    return proc.stdout, proc.stderr


def extract_ocrized_text(pdf_file, txt_output_file):
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for p in pdf_f.pages():
            text += p.get_text()
    with open(txt_output_file, "w", encoding='utf-8') as txt_f:
        txt_f.write(text)
