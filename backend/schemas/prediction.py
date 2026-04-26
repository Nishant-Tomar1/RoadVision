from typing import Optional

from pydantic import BaseModel, Field


class ClassCount(BaseModel):
    class_name: str = Field(..., description="Detected class label")
    count: int = Field(..., ge=0, description="Number of unique tracked instances")


class PredictionResult(BaseModel):
    video_url: str
    download_url: str
    counts: list[ClassCount]
    total_unique_objects: int
    frames_processed: int
    inference_seconds: float


class JobAccepted(BaseModel):
    job_id: str
    status: str
    total_frames: int
    status_url: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float = Field(..., ge=0.0, le=1.0)
    frames_processed: int
    total_frames: int
    elapsed_seconds: float
    eta_seconds: Optional[float] = None
    error: Optional[str] = None
    result: Optional[PredictionResult] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    classes: list[str]
