from fastapi import File, UploadFile
from pydantic import BaseModel


class OCRRequest(BaseModel):
    """Request payload for the OCR endpoint"""

    pdf_file: UploadFile = None


class OCRResponse(BaseModel):
    """Response payload for the OCR endpoint"""

    pdf_file: File = None


class QualityEstimation(BaseModel):
    """Response payload for the OCR endpoint"""

    job_id: str = None
    quality: float = None
