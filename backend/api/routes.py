import logging
import shutil
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from config import settings
from schemas.prediction import (
    HealthResponse,
    JobAccepted,
    JobStatus,
    PredictionResult,
)
from services.detector import (
    DetectorNotReadyError,
    count_video_frames,
    detector,
)
from services.jobs import jobs

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=detector.is_ready,
        classes=settings.CLASS_NAMES,
    )


@router.post("/predict", response_model=JobAccepted, status_code=202)
async def predict(request: Request, file: UploadFile = File(...)) -> JobAccepted:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        logger.warning("Rejected upload '%s' (bad extension %s)", file.filename, suffix)
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    if not detector.is_ready:
        raise HTTPException(status_code=503, detail="Model not loaded yet — try again in a moment.")

    job_id = uuid.uuid4().hex
    upload_path = settings.UPLOAD_DIR / f"{job_id}{suffix}"
    logger.info("[job %s] receiving '%s' → %s", job_id, file.filename, upload_path.name)

    size = 0
    try:
        with upload_path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    logger.warning("[job %s] upload exceeded %d bytes", job_id, settings.MAX_UPLOAD_SIZE)
                    upload_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="File too large")
                out.write(chunk)
    finally:
        await file.close()

    total_frames = count_video_frames(upload_path)
    logger.info("[job %s] upload complete (%.2f MB, %d frames) — queueing", job_id, size / (1024 * 1024), total_frames)

    state = jobs.create(job_id, total_frames=total_frames)
    base_url = str(request.base_url).rstrip("/")

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, upload_path, base_url),
        daemon=True,
    )
    thread.start()

    return JobAccepted(
        job_id=job_id,
        status=state.status,
        total_frames=total_frames,
        status_url=f"{base_url}/jobs/{job_id}",
    )


def _run_job(job_id: str, upload_path: Path, base_url: str) -> None:
    try:
        result = detector.predict_video(
            upload_path,
            job_id,
            progress_cb=lambda frames: jobs.set_progress(job_id, frames),
        )
        prediction = PredictionResult(
            video_url=f"{base_url}/results/{job_id}/video",
            download_url=f"{base_url}/results/{job_id}/download",
            counts=result["counts"],
            total_unique_objects=result["total_unique_objects"],
            frames_processed=result["frames_processed"],
            inference_seconds=result["inference_seconds"],
        )
        jobs.mark_done(job_id, prediction.model_dump())
        counts_str = ", ".join(f"{c['class_name']}={c['count']}" for c in result["counts"])
        logger.info(
            "[job %s] done in %.2fs — frames=%d, total=%d, %s",
            job_id, result["inference_seconds"], result["frames_processed"],
            result["total_unique_objects"], counts_str,
        )
    except DetectorNotReadyError as exc:
        logger.error("[job %s] model not ready: %s", job_id, exc)
        jobs.mark_error(job_id, str(exc))
    except Exception as exc:
        logger.exception("[job %s] inference failed", job_id)
        jobs.mark_error(job_id, f"{type(exc).__name__}: {exc}")
    finally:
        upload_path.unlink(missing_ok=True)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str) -> JobStatus:
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id")
    state = jobs.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return JobStatus(
        job_id=state.job_id,
        status=state.status,
        progress=state.progress,
        frames_processed=state.frames_processed,
        total_frames=state.total_frames,
        elapsed_seconds=round(state.elapsed_seconds, 2),
        eta_seconds=round(state.eta_seconds, 2) if state.eta_seconds is not None else None,
        error=state.error,
        result=state.result,
    )


@router.get("/results/{job_id}/video", name="get_result_video")
def get_result_video(job_id: str) -> FileResponse:
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id")
    path = settings.RESULT_DIR / job_id / "annotated.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"},
    )


@router.get("/results/{job_id}/download", name="download_result_video")
def download_result_video(job_id: str) -> FileResponse:
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id")
    path = settings.RESULT_DIR / job_id / "annotated.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"roadvision-{job_id}.mp4",
    )


@router.delete("/results/{job_id}")
def delete_result(job_id: str) -> dict:
    if not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job id")
    run_dir = settings.RESULT_DIR / job_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    jobs.remove(job_id)
    return {"deleted": job_id}
