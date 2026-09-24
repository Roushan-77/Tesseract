from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://tesseract:tesseract@localhost:5432/tesseract"
    jwt_secret: str = "local-development-secret"
    demo_password: str = "demo-password"
    jwt_algorithm: str = "HS256"
    tesseract_cmd: str | None = None
    pdftoppm_cmd: str | None = None
    tesseract_lang: str = "eng+hin"
    neo4j_uri: str | None = None
    neo4j_username: str = "neo4j"
    neo4j_password: str | None = None
    cors_origins: str = "*"
    storage_root: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    # This stays stable when Alembic or Uvicorn is launched from another folder.
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

settings = Settings()

