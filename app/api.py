import logging
import os
from typing import Any, Dict, Union

from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.constants import JobSpec, Status

from .controllers import ocr_controller

LOGGER = logging.getLogger(__name__)
CONTEXT: Dict[str, Dict[str, Any]] = {}


tags_metadata = [
    {
        "name": "test_ocr",
        "description": "[To be deprecated]. Perform OCR on the PDF and return the PDF result. No jobs involved. Operation is blocking.",
    },
    {
        "name": "ocr",
        "description": "Currently operation is blocking. Perform OCR on a given PDF and job id. The job id has the pdf, text and other properties attached.",
    },
    {
        "name": "status",
        "description": "Get the status of the job. The status can be one of processing, complete or failed.",
    },
    {
        "name": "pdf",
        "description": "Get the PDF file for the job.",
    },
    {"name": "text", "description": "Get the text file for the job."},
    {
        "name": "quality",
        "description": "Get the quality of the OCR process for the job.",
    },
    {"name": "highlight", "description": "Get the PDF file with keywords highlighted."},
]


# Set up the app
app = FastAPI(openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)

# Set up the routes


@app.post("/test_ocr", tags=["test_ocr"])
async def ocr_simple(file: UploadFile = File(...)):
    """Perform OCR on the PDF and render the result"""
    return ocr_controller.ocr_simple(file)


def do_work(job_id: str, file):
    (
        CONTEXT[job_id][JobSpec.PDF_PATH],
        CONTEXT[job_id][JobSpec.TEXT_PATH],
        CONTEXT[job_id][JobSpec.ANALYZED_PDF_PATH],
    ) = ocr_controller.run_ocr(job_id, file)
    CONTEXT[job_id][JobSpec.STATUS] = Status.COMPLETE


@app.post("/ocr_b", tags=["ocr"])
def ocr_b(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_id: Union[str, None] = Header(default=None, convert_underscores=False),
):
    CONTEXT[job_id] = {JobSpec.STATUS: Status.PROCESSING}
    background_tasks.add_task(do_work, job_id, file)
    return {JobSpec.ID: job_id}


@app.post("/ocr", tags=["ocr"])
def ocr(
    file: UploadFile = File(...),
    job_id: Union[str, None] = Header(default=None, convert_underscores=False),
):
    CONTEXT[job_id] = {JobSpec.STATUS: Status.PROCESSING}
    do_work(job_id, file)
    return {JobSpec.ID: job_id}


def assert_job_done(job_id: str):
    if job_id not in CONTEXT:
        raise HTTPException(status_code=404, detail="Job not found")
    if CONTEXT[job_id][JobSpec.STATUS] not in {Status.COMPLETE, Status.WB_FAILED}:
        raise HTTPException(status_code=422, detail="Job not complete")


@app.get("/ocr/{job_id}/status", tags=["status"])
async def get_status(job_id: str):
    if job_id not in CONTEXT:
        raise HTTPException(status_code=404, detail="Job not found")
    return {JobSpec.STATUS: CONTEXT[job_id][JobSpec.STATUS]}


@app.get("/ocr/{job_id}/pdf", tags=["pdf"])
async def get_pdf_result(job_id: str):
    assert_job_done(job_id)
    down_file = CONTEXT[job_id][JobSpec.PDF_PATH]
    headers = {
        "Content-Disposition": f"attachment; filename={os.path.basename(down_file)}"
    }
    return FileResponse(path=down_file, media_type="application/pdf", headers=headers)


@app.get("/ocr/{job_id}/text", tags=["text"])
async def get_result(job_id: str):
    assert_job_done(job_id)
    down_file = CONTEXT[job_id][JobSpec.TEXT_PATH]
    headers = {
        "Content-Disposition": f"attachment; filename={os.path.basename(down_file)}"
    }
    return FileResponse(path=down_file, media_type="text/plain", headers=headers)


@app.get("/ocr/{job_id}/analyze_pdf", tags=["highlight"])
async def get_analyzed_result(job_id: str):
    assert_job_done(job_id)
    orig_pdf_file = CONTEXT[job_id][JobSpec.PDF_PATH]
    down_file = CONTEXT[job_id][JobSpec.ANALYZED_PDF_PATH]
    ocr_controller.analyze_pdf(orig_pdf_file, down_file)
    headers = {
        "Content-Disposition": f"attachment; filename={os.path.basename(down_file)}"
    }
    return FileResponse(path=down_file, media_type="application/pdf", headers=headers)


@app.get("/ocr/{job_id}/quality", tags=["quality"])
async def quality(job_id):
    assert_job_done(job_id)
    # TODO: optimize? (only process file once)
    down_text_file = CONTEXT[job_id][JobSpec.TEXT_PATH]
    CONTEXT[job_id][JobSpec.QUALITY] = ocr_controller.estimate_quality(down_text_file)
    return {"ocr_quality_percent": CONTEXT[job_id][JobSpec.QUALITY]}


@app.get("/")
async def root():
    return {"message": "Amazing software 𓀃"}
