import logging
import os
from subprocess import run
from typing import Tuple

import fitz
import pikepdf
from ocrmypdf.__main__ import run as run_ocrmypdf
from ocrmypdf._exec import tesseract

from app.config import BACK_LANG, LEGAL_LANG, MAX_PAGE_PDF_A, NUM_PROC
from app.services.text_processing import Cleaner

logger = logging.getLogger(__name__)


def get_language() -> str:
    """Get the language to use for OCR."""
    tess_languages = tesseract.get_languages()
    return LEGAL_LANG if LEGAL_LANG in tess_languages else BACK_LANG


LANGUAGE = get_language()
logger.info(f"Using language {LANGUAGE} for OCR")


WORD_LIST = "nlp/resources/custom-wordlist.txt"
USER_WORDS = []
if os.path.exists(WORD_LIST):
    USER_WORDS = ["--user-words", WORD_LIST]


CMD_ARGS = [
    "--skip-text",
    "--rotate-pages",
    "--language",
    LANGUAGE,
    "--jobs",
    str(NUM_PROC),
    "--tesseract-timeout",
    "600",
] + USER_WORDS
# some PDF files might not be convertible to PDF/A
# then we try again with --output-type pdf
# for efficiency reasons, large files
# should not be converted because it takes too long
FAIL_SAFE_ARGS = ["--output-type", "pdf"]
FORCE_ROTATE_ARGS = ["--rotate-pages-threshold", "9"]
CMD_ARGS.extend(["-v", "2"])

OCRMYPDF = "ocrmypdf"


def is_pdf_valid(input_file: str) -> bool:
    """Check if a PDF is valid."""
    try:
        with pikepdf.open(input_file) as _:
            pass
    except pikepdf.PdfError:
        logger.exception(f"Invalid PDF: {input_file}")
        return False  # invalid PDF
    return True


def is_pdf_encrypted(pdf_file_path: str) -> bool:
    """Check if a PDF is encrypted."""
    with fitz.Document(pdf_file_path) as doc:
        if doc.needs_pass or doc.metadata is None or doc.is_encrypted:
            return True
        if doc.metadata is not None and doc.metadata.get("encryption", ""):
            return True
    return False


def count_pages(pdf_file_path: str) -> int:
    """Count the number of pages in a PDF file."""
    with fitz.Document(pdf_file_path) as doc:
        return doc.page_count


def remove_encryption(pdf_file_path: str):
    """Removes encryption by resaving the document."""
    logger.info(f"Saving unencrypted document: {pdf_file_path}")
    with pikepdf.open(pdf_file_path, allow_overwriting_input=True) as doc:
        doc.save(pdf_file_path)


def make_ocr_command(
    in_file: str, pdf_output: str, pdf_a: bool = True, force_rotate: bool = False
) -> Tuple[str, bool]:
    """Make the OCR command and check if we have a large number of pages."""
    ocrmypdf_args = [OCRMYPDF, in_file, pdf_output, *CMD_ARGS]
    large_page_count = count_pages(in_file) > MAX_PAGE_PDF_A
    if pdf_a is False or large_page_count:
        ocrmypdf_args = [OCRMYPDF, in_file, pdf_output, *FAIL_SAFE_ARGS, *CMD_ARGS]
    if force_rotate:
        ocrmypdf_args.extend(FORCE_ROTATE_ARGS)
    logger.debug(" ".join(ocrmypdf_args))
    return ocrmypdf_args, large_page_count


def run_ocr_natively(in_file: str, pdf_output: str, force_rotate: bool):
    """Run OCR using the ocrmypdf library."""
    ocrmypdf_args, _ = make_ocr_command(
        in_file, pdf_output, pdf_a=False, force_rotate=force_rotate
    )
    status_code = run_ocrmypdf(ocrmypdf_args)
    if status_code != 0:
        raise Exception("Failed to do OCR.")


def call_ocr(in_file: str, pdf_output: str, force_rotate: bool) -> Tuple[str, str]:
    """Call OCR using the ocrmypdf subprocess."""
    ocrmypdf_args, _ = make_ocr_command(
        in_file, pdf_output, pdf_a=False, force_rotate=force_rotate
    )
    proc = run(ocrmypdf_args, capture_output=True, encoding="utf-8")
    if proc.returncode != 0:
        logger.error(proc.stdout)
        logger.error(proc.stderr)
        # sometimes the PDF is not entirely valid according to the spec
        # but the generated PDF can still be used and rendered
        if not is_pdf_valid(pdf_output):
            raise Exception(proc.stderr)
    return proc.stdout, proc.stderr


def get_ocrized_text(pdf_file: str) -> str:
    """Get the OCRized text from a PDF file."""
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for page in pdf_f.pages():
            text += page.get_text()
    return text


def get_ocrized_text_from_blocks(pdf_file: str) -> str:
    """Get the OCRized text from a PDF file in a clean format using blocks."""
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for page in pdf_f.pages():
            blocks = page.get_text(option="blocks", flags=fitz.TEXTFLAGS_SEARCH)
            text += "\n".join([block[4].replace("\n", " ") for block in blocks]) + "\n"
    text = Cleaner().clean(text)
    return text


def dump_text(text: str, txt_output_file: str):
    """Dump text to a file."""
    with open(txt_output_file, "w", encoding="utf-8") as txt_f:
        txt_f.write(text)
