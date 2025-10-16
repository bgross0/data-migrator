from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Data Migrator"
    VERSION: str = "0.1.0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Odoo
    ODOO_URL: str | None = None
    ODOO_DB: str | None = None
    ODOO_USERNAME: str | None = None
    ODOO_PASSWORD: str | None = None

    # LLM
    ANTHROPIC_API_KEY: str | None = None

    # Storage
    STORAGE_PATH: str = "../storage"

    # Field Mapper - Odoo Dictionary Path
    ODOO_DICTIONARY_PATH: str = "../odoo-dictionary"

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Export settings (Commit 5)
    MODE: str = "lean"  # lean or scale
    RUNNER: str = "inline"  # inline or thread or celery
    ARTIFACT_ROOT: str = "./out"  # Output directory for exports
    REGISTRY_FILE: str = "registry/odoo.yaml"  # Path to registry YAML


settings = Settings()
