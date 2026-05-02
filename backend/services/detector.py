"""YOLO + ByteTrack inference service.

Mirrors the Colab pipeline (cells 12-15 of Untitled0.ipynb): load weights once,
run model.track() on a video, count unique track IDs per class, then transcode
the annotated AVI that Ultralytics writes into a browser-friendly MP4.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

import cv2
import requests
import torch
from ultralytics import YOLO

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


class Detector:
    def __init__(self) -> None:
        self._model: YOLO | None = None
        self._device: int | str = 0 if torch.cuda.is_available() else "cpu"

    def load(self) -> None:
        weights = settings.model_full_path
        if not weights.exists():
            raise DetectorNotReadyError(
                f"YOLO weights not found at {weights}. "
                "Place best.pt under backend/model/ or set MODEL_PATH."
            )
        logger.info("Loading YOLO weights from %s on device=%s", weights, self._device)
        self._model = YOLO(str(weights))

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def predict_video(
        self,
        source_path: Path,
        job_id: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> dict:
        if self._model is None:
            raise DetectorNotReadyError("Model has not been loaded yet.")

        run_dir = settings.RESULT_DIR / job_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

        logger.info(
            "[job %s] running model.track on %s (conf=%.2f iou=%.2f device=%s)",
            job_id, source_path.name, settings.CONF_THRESHOLD, settings.IOU_THRESHOLD, self._device,
        )
        started = time.perf_counter()
        results = self._model.track(
            source=str(source_path),
            conf=settings.CONF_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            tracker=settings.TRACKER,
            persist=True,
            save=True,
            stream=True,
            device=self._device,
            project=str(settings.RESULT_DIR),
            name=job_id,
            exist_ok=True,
            verbose=False,
        )

        unique_ids: dict[int, set[int]] = defaultdict(set)
        frames = 0
        for r in results:
            frames += 1
            if r.boxes is not None and r.boxes.id is not None:
                ids = r.boxes.id.cpu().numpy()
                classes = r.boxes.cls.cpu().numpy()
                for obj_id, cls in zip(ids, classes):
                    unique_ids[int(cls)].add(int(obj_id))
            if progress_cb is not None:
                progress_cb(frames)
            if frames % 30 == 0:
                running = ", ".join(
                    f"{settings.CLASS_NAMES[c]}={len(ids)}" for c, ids in sorted(unique_ids.items())
                ) or "no detections yet"
                logger.info("[job %s] processed %d frames — %s", job_id, frames, running)

        annotated = self._locate_annotated_video(run_dir)
        playable = run_dir / "annotated.mp4"
        self._transcode_to_mp4(annotated, playable)

        elapsed = time.perf_counter() - started
        counts = [
            {"class_name": settings.CLASS_NAMES[cls], "count": len(ids)}
            for cls, ids in sorted(unique_ids.items())
        ]
        for idx, name in enumerate(settings.CLASS_NAMES):
            if not any(c["class_name"] == name for c in counts):
                counts.append({"class_name": name, "count": 0})

        return {
            "video_path": playable,
            "counts": counts,
            "total_unique_objects": sum(len(ids) for ids in unique_ids.values()),
            "frames_processed": frames,
            "inference_seconds": round(elapsed, 2),
        }

    @staticmethod
    def _locate_annotated_video(run_dir: Path) -> Path:
        for ext in (".mp4", ".avi"):
            for path in run_dir.glob(f"*{ext}"):
                return path
        raise FileNotFoundError(f"No annotated video produced in {run_dir}")

    @staticmethod
    def _transcode_to_mp4(src: Path, dst: Path) -> None:
        """Re-encode to H.264 + AAC so browsers can play it inline.

        Falls back to a plain copy if ffmpeg isn't available — if Ultralytics
        already wrote MP4 (newer versions do), the copy is enough.
        """
        if shutil.which("ffmpeg") is None:
            shutil.copyfile(src, dst)
            return
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(src),
                    "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                    "-acodec", "aac", "-movflags", "+faststart",
                    str(dst),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            logger.warning("ffmpeg transcode failed; serving raw output instead")
            shutil.copyfile(src, dst)


class RemoteDetector:
    """Forwards inference to a remote GPU server (Colab + ngrok)."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def load(self) -> None:
        try:
            r = requests.get(f"{self._base_url}/health", timeout=10)
            r.raise_for_status()
            logger.info("Connected to remote GPU at %s", self._base_url)
        except requests.RequestException as exc:
            logger.warning("Remote GPU not reachable yet at %s: %s", self._base_url, exc)

    @property
    def is_ready(self) -> bool:
        return True

    def predict_video(
        self,
        source_path: Path,
        job_id: str,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> dict:
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


def _build_detector():
    url = (settings.GPU_INFERENCE_URL or "").strip()
    if url:
        logger.info("Using remote GPU detector at %s", url)
        return RemoteDetector(url)
    logger.info("Using local detector")
    return Detector()


detector = _build_detector()
