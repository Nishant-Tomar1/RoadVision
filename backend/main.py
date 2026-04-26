import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import settings
from services.detector import DetectorNotReadyError, detector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pothole-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        detector.load()
        logger.info("Model ready.")
    except DetectorNotReadyError as exc:
        logger.error("Model failed to load: %s", exc)
    yield


app = FastAPI(
    title="Pothole / Crack / Manhole Detection API",
    description="YOLO + ByteTrack inference over uploaded road videos.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    started = time.perf_counter()
    client = request.client.host if request.client else "?"
    logger.info("→ [%s] %s %s  (from %s)", req_id, request.method, request.url.path, client)
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        logger.exception("✗ [%s] crashed after %.0f ms", req_id, elapsed)
        raise
    elapsed = (time.perf_counter() - started) * 1000
    logger.info("← [%s] %s %s  status=%d  (%.0f ms)", req_id, request.method, request.url.path, response.status_code, elapsed)
    return response


app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"service": "pothole-detection-api", "docs": "/docs"}
