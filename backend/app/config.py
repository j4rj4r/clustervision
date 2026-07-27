from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "dev"
    cluster_name: str = "kubernetes"
    cluster_api_url: str = ""
    registry_namespace: str = "clustervision"
    registry_configmap: str = "user-registry"
    clusters_secret: str = "clustervision-clusters"
    cors_origins: list[str] = []
    # Public URL used in bootstrap scripts — auto-detected from request if empty
    public_url: str = ""

    # Vault integration (optional)
    vault_enabled: bool = False
    vault_addr: str = ""
    vault_token: str = ""
    vault_mount: str = "secret"
    vault_base_path: str = "clustervision/users"
    vault_namespace: str = ""
    vault_tls_skip_verify: bool = False

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
