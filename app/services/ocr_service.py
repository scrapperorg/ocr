import logging
import os
from subprocess import run

import fitz
import pikepdf
from ocrmypdf.__main__ import run as run_ocrmypdf
from ocrmypdf._exec import tesseract

LEGAL_LANG = "ro_legal"
BACK_LANG = "ron"
# number of parallel processes to use for OCR
NUM_PROC = str(os.environ.get("NUM_PROC", 1))

# maximum number of pages to convert to PDF/A
# otherwise output type is PDF
MAX_PAGE_PDF_A = 50

LOGGER = logging.getLogger(__name__)


def get_language():
    tess_languages = tesseract.get_languages()
    return LEGAL_LANG if LEGAL_LANG in tess_languages else BACK_LANG


LANGUAGE = get_language()
LOGGER.info(f"Using language {LANGUAGE} for OCR")


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
        LOGGER.exception(f"Invalid PDF: {input_file}")
        return False  # invalid PDF
    return True


def is_pdf_encrypted(pdf_file_path: str) -> bool:
    with fitz.Document(pdf_file_path) as doc:
        if doc.needs_pass or doc.metadata is None or doc.is_encrypted:
            return True
        if doc.metadata is not None and doc.metadata.get("encryption", ""):
            return True
    return False


def count_pages(pdf_file_path: str) -> int:
    with fitz.Document(pdf_file_path) as doc:
        return doc.page_count


def remove_encryption(pdf_file_path: str):
    """Removes encryption by resaving the document

    Args:
        pdf_file_path (str): pdf file path
    """
    LOGGER.info(f"Saving unencrypted document: {pdf_file_path}")
    with pikepdf.open(pdf_file_path, allow_overwriting_input=True) as doc:
        doc.save(pdf_file_path)


def make_ocr_command(in_file, pdf_output, pdf_a=True, force_rotate=False):
    ocrmypdf_args = [OCRMYPDF, in_file, pdf_output, *CMD_ARGS]
    large_page_count = count_pages(in_file) > MAX_PAGE_PDF_A
    if pdf_a is False or large_page_count:
        ocrmypdf_args = [OCRMYPDF, in_file, pdf_output, *FAIL_SAFE_ARGS, *CMD_ARGS]
    if force_rotate:
        ocrmypdf_args.extend(FORCE_ROTATE_ARGS)
    LOGGER.debug(" ".join(ocrmypdf_args))
    return ocrmypdf_args, large_page_count


def run_ocr_natively(in_file, pdf_output, force_rotate):
    ocrmypdf_args, _ = make_ocr_command(
        in_file, pdf_output, pdf_a=False, force_rotate=force_rotate
    )
    status_code = run_ocrmypdf(ocrmypdf_args)
    if status_code != 0:
        raise Exception("Failed to do OCR.")


def call_ocr(in_file, pdf_output, force_rotate):
    ocrmypdf_args, _ = make_ocr_command(
        in_file, pdf_output, pdf_a=False, force_rotate=force_rotate
    )
    proc = run(ocrmypdf_args, capture_output=True, encoding="utf-8")
    if proc.returncode != 0:
        LOGGER.error(proc.stdout)
        LOGGER.error(proc.stderr)
        # sometimes the PDF is not entirely valid according to the spec
        # but the generated PDF can still be used and rendered
        if not is_pdf_valid(pdf_output):
            raise Exception(proc.stderr)
    return proc.stdout, proc.stderr


def get_ocrized_text(pdf_file):
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for page in pdf_f.pages():
            text += page.get_text()
    return text


def get_ocrized_text_from_blocks(pdf_file):
    text = ""
    with fitz.open(pdf_file) as pdf_f:
        for page in pdf_f.pages():
            blocks = page.get_text(option="blocks", flags=fitz.TEXTFLAGS_SEARCH)
            text += "\n".join([block[4].replace("\n", " ") for block in blocks]) + "\n"
    return text


def extract_ocrized_text(pdf_file, txt_output_file):
    text = get_ocrized_text(pdf_file)
    dump_text(text, txt_output_file)
    return text


def dump_text(text, txt_output_file):
    with open(txt_output_file, "w", encoding="utf-8") as txt_f:
        txt_f.write(text)
