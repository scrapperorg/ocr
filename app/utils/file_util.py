import os
import re
import unicodedata
import uuid
from pathlib import Path

_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")


def secure_filename(filename: str) -> str:
    """Return a secure version of a filename."""
    filename, extension = os.path.splitext(filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    for sep in os.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip(
        "._"
    )
    if not filename.strip():
        filename = uuid.uuid4().hex
    return f"{filename}{extension}"


def make_download_file_path(file_path: str, suffix="ocr", new_extension=None) -> str:
    """Make the download file path"""
    filename = os.path.basename(file_path)
    work_folder = os.path.dirname(file_path)
    filename, extension = os.path.splitext(filename)
    if new_extension:
        extension = new_extension
    filename = f"{filename}_{suffix}{extension}"
    return os.path.join(work_folder, filename)


def make_derived_file_name(
    file_path: str, new_path=None, new_suffix="ocr", new_extension=None
) -> str:
    """Make the download file path"""
    filename = os.path.basename(file_path)
    work_folder = os.path.dirname(file_path)
    if new_path:
        work_folder = new_path
    filename, extension = os.path.splitext(filename)
    if new_extension:
        extension = new_extension
    filename = f"{filename}_{new_suffix}.{extension}"
    return os.path.join(work_folder, filename)


def upload(file, work_folder: Path) -> str:
    """Upload the file to the work folder"""
    secure_file_name = secure_filename(file.filename)
    up_file = os.path.join(work_folder, secure_file_name)
    with open(up_file, "wb") as fout:
        while contents := file.file.read(1024 * 1024):
            fout.write(contents)
    return up_file


def read_text_file(path):
    """Read text file"""
    with open(path, "r", encoding="utf-8") as fin:
        return fin.read()
