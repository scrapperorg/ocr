class ResponseField:
    WORKER = "worker_id"
    IN = "input_file"
    JOB_ID = "job_id"
    IN_STATUS = "input_status"
    OUT = "analysis_file"
    OCR = "ocr_file"
    ANALYSIS = "highlight_file"
    ANALYSIS_META = "highlight_metadata"
    TEXT_FILE = "text_file"
    TEXT = "text"
    QUALITY = "ocr_quality"
    STATISTICS = "statistics"
    TIME = "processing_time"
    WK_VERSION = "worker_version"
    KWDS_HASH = "keywords_hash"


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
    FAILED = "ocr_failed"
    NOT_FOUND = "not_found"

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
