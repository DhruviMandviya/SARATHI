from typing import List, Union
from pathlib import Path
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "SARATHI — AICTE Document Verification System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "aicte-super-secure-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR.as_posix()}/aicte_verifier.db"

    STORAGE_DIR: str = str(BASE_DIR / "storage")
    DERIVED_DIR: str = str(BASE_DIR / "storage" / "derived")
    MAX_FILE_SIZE_MB: int = 10
    MAX_PDF_PAGES: int = 20

    TESSERACT_CMD: str = ""
    OCR_LANG: str = "eng"
    LLM_EXTRACTION_ENABLED: bool = False

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure storage directories exist
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.DERIVED_DIR).mkdir(parents=True, exist_ok=True)
