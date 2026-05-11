from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    # Comma-separated origins, e.g. "http://localhost:3000,https://example.com"
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-3-lite"
    embedding_api_key: str = ""

    def get_allowed_origins(self) -> list:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
