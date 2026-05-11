from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "[YourBrand] Auto Sales AI API"
    app_env: str = "development"
    debug: bool = False

    database_url: str = "sqlite:///./[your_brand]_auto_sales.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    auto_run_migrations: bool = False

    public_sales_url: str = "https://[your-domain]"
    cors_origins: list[str] | str = [
        "https://[your-domain]",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]
    trusted_hosts: list[str] | str = ["*"]
    default_dealership_id: str = "dealer-001"
    dealership_header_name: str = "X-Dealership-ID"

    site_api_key: str | None = None
    require_site_api_key: bool = False
    site_api_key_header_name: str = "X-API-Key"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    semantic_vector_dimensions: int = 256
    openai_timeout_seconds: int = 30
    enable_openai: bool = False
    semantic_faiss_enabled: bool = False
    semantic_semantic_weight: float = Field(default=0.72, ge=0.0, le=1.0)
    semantic_lexical_weight: float = Field(default=0.28, ge=0.0, le=1.0)
    semantic_reply_candidates: int = Field(default=8, ge=3, le=20)

    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    internal_admin_token: str = "dev-internal-admin-token"

    email_notifications_enabled: bool = True
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 20

    email_from: str | None = None
    email_from_name: str = "[YourBrand] Auto Sales"
    email_reply_to: str | None = None
    appointment_email_subject_prefix: str = "[YourBrand] Auto"

    response_sla_minutes: int = 5
    enable_seeding: bool = True

    request_id_header_name: str = "X-Request-ID"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_csv_list(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "debug",
        "auto_run_migrations",
        "require_site_api_key",
        "enable_openai",
        "email_notifications_enabled",
        "enable_seeding",
        "semantic_faiss_enabled",
        mode="before",
    )
    @classmethod
    def parse_boolish(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "production", "prod", "false", "0", "off", "no"}:
                return False
            if lowered in {"development", "dev", "true", "1", "on", "yes", "test"}:
                return True
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def is_test(self) -> bool:
        return self.app_env.lower() == "test"

    @model_validator(mode="after")
    def validate_production_requirements(self):
        if self.semantic_semantic_weight + self.semantic_lexical_weight <= 0:
            raise ValueError("semantic scoring weights must add up to a positive value")
        if self.is_production:
            insecure_tokens = {"dev-only-change-me", "dev-internal-admin-token", "change-this-in-production", "[your-brand]-admin-dev-token"}
            if self.jwt_secret_key in insecure_tokens:
                raise ValueError("JWT_SECRET_KEY must be set to a non-default secret in production")
            if self.internal_admin_token in insecure_tokens:
                raise ValueError("INTERNAL_ADMIN_TOKEN must be set to a non-default secret in production")
            if self.require_site_api_key and not self.site_api_key:
                raise ValueError("SITE_API_KEY must be configured when REQUIRE_SITE_API_KEY=true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
