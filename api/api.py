import logging
import os
from typing import Any, Dict, Union

import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.middleware.cors import CORSMiddleware
from tenacity import before_log, retry, stop_after_attempt

from api.config import settings
from api.constants import JobSpec, Status

from .controllers import ocr_controller

LOGGER = logging.getLogger(__name__)
OCR_DONE_WEBHOOK = os.environ.get("OCR_DONE_WEBHOOK", "http://localhost:8081/ocr_done")
CONTEXT: Dict[str, Dict[str, Any]] = {}


tags_metadata = [
    {
        "name": "ocr_simple",
        "description": "Perform OCR on the PDF and return the PDF result. No jobs involved. Operation is blocking.",
    },
    {
        "name": "ocr",
        "description": "Currently operation is blocking, but that will change in the near future. Perform OCR on the PDF and return a job id. The job id has the pdf, text and other properties attached. Operation is non-blocking.",
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


@app.post("/ocr_simple", tags=["ocr_simple"])
async def ocr_simple(file: UploadFile = File(...)):
    """Perform OCR on the PDF and render the result"""
    return ocr_controller.ocr_simple(file)


@retry(stop=stop_after_attempt(3), before=before_log(LOGGER, logging.INFO))
def call_webhook(job_id):
    requests.post(OCR_DONE_WEBHOOK, json={"job_id": job_id})
    #raise Exception("Webhook failed!")


async def do_work(job_id, file):
    (
        CONTEXT[job_id][JobSpec.PDF_PATH],
        CONTEXT[job_id][JobSpec.TEXT_PATH],
        CONTEXT[job_id][JobSpec.ANALYZED_PDF_PATH],
    ) = await ocr_controller.run_ocr(file)
    status = Status.COMPLETE
    try:
        call_webhook(job_id)
    except Exception as e:
        LOGGER.exception(e)
        status = Status.WB_FAILED
    CONTEXT[job_id][JobSpec.STATUS] = status


@app.post("/ocr", tags=["ocr"])
async def ocr(
    file: UploadFile = File(...),
    job_id: Union[str, None] = Header(default=None, convert_underscores=False),
):
    # job_id = str(uuid.uuid4().hex)
    CONTEXT[job_id] = {JobSpec.STATUS: Status.PROCESSING}
    # Run OCR on the file asynchronously
    # asyncio.run_coroutine_threadsafe(do_work(job_id, file), loop=asyncio.get_running_loop())
    await do_work(job_id, file)
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


# Start the server
# if __name__ == '__main__':
#    uvicorn.run(app, host='0.0.0.0', port=8080)
