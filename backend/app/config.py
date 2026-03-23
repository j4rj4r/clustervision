from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    cluster_name: str = "kubernetes"
    cluster_api_url: str = ""
    registry_namespace: str = "clustervision"
    registry_configmap: str = "user-registry"
    cors_origins: list[str] = []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v or v == "[]":
                return []
            # JSON array: '["https://example.com"]'
            if v.startswith("["):
                import json
                return json.loads(v)
            # Comma-separated fallback
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
