"""Remote GPU inference client.

Forwards the upload to a Colab-hosted FastAPI server (exposed via ngrok) which
runs YOLO + ByteTrack on a GPU and returns the annotated MP4 + counts.
"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import requests

from config import settings

logger = logging.getLogger(__name__)


class DetectorNotReadyError(RuntimeError):
    pass


def count_video_frames(path: Path) -> int:
    cap = cv2.VideoCapture(str(path))
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()
    return max(0, total)


class RemoteDetector:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def load(self) -> None:
        if not self._base_url:
            logger.warning("GPU_INFERENCE_URL is empty — predict calls will fail.")
            return
        try:
            r = requests.get(f"{self._base_url}/health", timeout=10)
            r.raise_for_status()
            logger.info("Connected to remote GPU at %s", self._base_url)
        except requests.RequestException as exc:
            logger.warning("Remote GPU not reachable yet at %s: %s", self._base_url, exc)

    @property
    def is_ready(self) -> bool:
        return bool(self._base_url)

    def predict_video(
        self,
        source_path: Path,
        job_id: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> dict:
        if not self._base_url:
            raise DetectorNotReadyError("GPU_INFERENCE_URL not configured.")

        run_dir = settings.RESULT_DIR / job_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        logger.info("[job %s] forwarding to remote GPU at %s", job_id, self._base_url)
        started = time.perf_counter()

        with source_path.open("rb") as fh:
            files = {"file": (source_path.name, fh, "video/mp4")}
            resp = requests.post(
                f"{self._base_url}/predict",
                files=files,
                timeout=settings.GPU_INFERENCE_TIMEOUT,
            )
        resp.raise_for_status()
        meta = resp.json()
        remote_job_id = meta["job_id"]

        playable = run_dir / "annotated.mp4"
        with requests.get(
            f"{self._base_url}/video/{remote_job_id}",
            stream=True,
            timeout=settings.GPU_INFERENCE_TIMEOUT,
        ) as vr:
            vr.raise_for_status()
            with playable.open("wb") as out:
                for chunk in vr.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        out.write(chunk)

        if progress_cb is not None:
            progress_cb(meta.get("frames_processed", 0))

        elapsed = time.perf_counter() - started
        logger.info("[job %s] remote inference done in %.2fs", job_id, elapsed)

        return {
            "video_path": playable,
            "counts": meta["counts"],
            "total_unique_objects": meta["total_unique_objects"],
            "frames_processed": meta["frames_processed"],
            "inference_seconds": meta.get("inference_seconds", round(elapsed, 2)),
        }


detector = RemoteDetector((settings.GPU_INFERENCE_URL or "").strip())
