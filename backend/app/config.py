from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    cluster_name: str = "kubernetes"
    cluster_api_url: str = ""
    registry_namespace: str = "clustervision"
    registry_configmap: str = "user-registry"

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
