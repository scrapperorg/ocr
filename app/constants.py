from enum import Enum

DB_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Status:
    COMPLETE = "complete"
    FAILED = "failed"
    PROCESSING = "processing"
    WB_FAILED = "complete, but webhook_failed"


class APIStatus:
    DOWNLOADED = "downloaded"
    LOCKED = "locked"
    OCR_INPROGRESS = "ocr_in_progress"
    OCR_DONE = "ocr_done"

    @staticmethod
    def statuses() -> str:
        return str(
            set(
                [
                    APIStatus.DOWNLOADED,
                    APIStatus.LOCKED,
                    APIStatus.OCR_DONE,
                    APIStatus.OCR_INPROGRESS,
                ]
            )
        )


class JobSpec:
    PDF_PATH = "pdf_path"
    TEXT_PATH = "text_path"
    ANALYZED_PDF_PATH = "analyzed_pdf_path"
    STATUS = "status"
    ID = "job_id"
    QUALITY = "quality"


class Environment(str, Enum):
    LOCAL = "LOCAL"
    STAGING = "STAGING"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"

    @property
    def is_debug(self):
        return self in (self.LOCAL, self.STAGING, self.TESTING)

    @property
    def is_testing(self):
        return self == self.TESTING

    @property
    def is_deployed(self) -> bool:
        return self in (self.STAGING, self.PRODUCTION)
