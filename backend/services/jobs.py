"""In-memory job tracker for async inference.

Holds per-job progress so the frontend can poll while inference runs in a
background thread. Single-process only (no Redis/db) — fine for a BTP demo.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional


@dataclass
class JobState:
    job_id: str
    status: str = "queued"  # queued | processing | done | error
    total_frames: int = 0
    frames_processed: int = 0
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at or time.time()
        return max(0.0, end - self.started_at)

    @property
    def progress(self) -> float:
        if self.status == "done":
            return 1.0
        if self.total_frames <= 0:
            return 0.0
        return min(1.0, self.frames_processed / self.total_frames)

    @property
    def eta_seconds(self) -> Optional[float]:
        if self.status != "processing" or self.frames_processed <= 0:
            return None
        elapsed = self.elapsed_seconds
        if elapsed <= 0:
            return None
        rate = self.frames_processed / elapsed
        if rate <= 0:
            return None
        remaining = max(0, self.total_frames - self.frames_processed)
        return remaining / rate


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = Lock()

    def create(self, job_id: str, total_frames: int) -> JobState:
        with self._lock:
            state = JobState(job_id=job_id, total_frames=total_frames, status="processing")
            self._jobs[job_id] = state
            return state

    def get(self, job_id: str) -> Optional[JobState]:
        with self._lock:
            return self._jobs.get(job_id)

    def set_progress(self, job_id: str, frames_processed: int) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is not None:
                state.frames_processed = frames_processed

    def mark_done(self, job_id: str, result: dict) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is not None:
                state.status = "done"
                state.result = result
                state.finished_at = time.time()
                state.frames_processed = state.total_frames or state.frames_processed

    def mark_error(self, job_id: str, error: str) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is not None:
                state.status = "error"
                state.error = error
                state.finished_at = time.time()

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)


jobs = JobManager()
