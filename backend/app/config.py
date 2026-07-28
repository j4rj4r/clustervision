from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "dev"
    cluster_name: str = "kubernetes"
    cluster_api_url: str = ""
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

    # Required PostgreSQL database — all ClusterVision application state
    # (local login accounts, managed user registry, token history, cluster
    # registry, Vault runtime config, access requests) is stored here. Native
    # Kubernetes objects the app manages (RBAC objects, CSRs, ServiceAccount
    # token Secrets) are unaffected — those must remain in Kubernetes.
    database_url: str

    # LDAP / Active Directory integration (optional)
    ldap_enabled: bool = False
    ldap_url: str = ""                     # e.g. ldaps://dc01.company.local:636
    ldap_bind_dn: str = ""                 # service account used to search for the user's DN
    ldap_bind_password: str = ""
    ldap_user_search_base: str = ""        # e.g. OU=Users,DC=company,DC=local
    ldap_user_search_filter: str = "(sAMAccountName={username})"
    ldap_admin_group_dn: str = ""          # members of this group get the admin role
    ldap_viewer_group_dn: str = ""         # empty = any successful bind gets viewer
    ldap_tls_skip_verify: bool = False

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
