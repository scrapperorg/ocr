import asyncio
import logging
from subprocess import run
from nlp.resources.constants import WORDLIST_PATH

LOGGER = logging.getLogger(__name__)

CMD_ARGS = ["--skip-text", "-l", "ron", "--user-words", WORDLIST_PATH]
OCRMYPDF = "ocrmypdf"


def call_ocr(in_file, pdf_output, txt_output):
    LOGGER.debug("Wordlist:" + WORDLIST_PATH)
    cmd_args = CMD_ARGS + ["--sidecar", txt_output]
    ocrmypdf_args = [OCRMYPDF, *cmd_args, in_file, pdf_output]
    proc = run(ocrmypdf_args, capture_output=True, encoding="utf-8")
    if proc.returncode != 0:
        LOGGER.error(proc.stderr)
        raise Exception(proc.stderr)
    LOGGER.debug(proc.stdout)
    LOGGER.debug(proc.stderr)
    return proc.stdout, proc.stderr


async def call_ocr_async(in_file, pdf_output, txt_output):
    # sub process is here, and here is where the exception happens.
    # TODO: when --sidecar is provided and the pdf already has text,
    # the cmd skips all pages with text
    cmd_args = CMD_ARGS + ["--sidecar", txt_output]
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
