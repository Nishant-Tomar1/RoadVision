from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MODEL_PATH: str = "model/best.pt"
    CONF_THRESHOLD: float = 0.3
    IOU_THRESHOLD: float = 0.5
    TRACKER: str = "bytetrack.yaml"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    CORS_ORIGINS: str = "*"

    GPU_INFERENCE_URL: str = ""
    GPU_INFERENCE_TIMEOUT: int = 1200

    CLASS_NAMES: list[str] = ["pothole", "crack", "manhole"]

    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: Path = Path(__file__).resolve().parent / "storage" / "uploads"
    RESULT_DIR: Path = Path(__file__).resolve().parent / "storage" / "results"

    @property
    def model_full_path(self) -> Path:
        p = Path(self.MODEL_PATH)
        return p if p.is_absolute() else self.BASE_DIR / p

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULT_DIR.mkdir(parents=True, exist_ok=True)
