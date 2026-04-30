import json
import logging
import os

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

_VAULT_CONFIG_KEY = "vault_config"


class VaultError(Exception):
    pass


class VaultService:
    """
    Thin Vault KV v2 client (no hvac dependency — plain HTTP).
    Config can be supplied at construction time or loaded from env.
    """

    def __init__(self, addr: str, token: str, mount: str = "secret", base_path: str = "clustervision/users", namespace: str = ""):
        self.addr = addr.rstrip("/")
        self.token = token
        self.mount = mount.strip("/")
        self.base_path = base_path.strip("/")
        self.namespace = namespace  # Vault Enterprise namespace header

    # ── KV v2 write ────────────────────────────────────────────────────────

    def write_secret(self, username: str, data: dict) -> str:
        """Write key data to Vault KV v2. Returns the full Vault path."""
        path = f"{self.base_path}/{username}"
        url = f"{self.addr}/v1/{self.mount}/data/{path}"
        payload = json.dumps({"data": data}).encode()
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Vault-Token", self.token)
        if self.namespace:
            req.add_header("X-Vault-Namespace", self.namespace)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise VaultError(f"Vault write failed ({e.code}): {body}") from e
        except Exception as e:
            raise VaultError(f"Vault connection failed: {e}") from e
        return f"{self.mount}/data/{path}"

    def read_secret(self, username: str) -> dict:
        path = f"{self.base_path}/{username}"
        url = f"{self.addr}/v1/{self.mount}/data/{path}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("X-Vault-Token", self.token)
        if self.namespace:
            req.add_header("X-Vault-Namespace", self.namespace)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["data"]["data"]
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            raise VaultError(f"Vault read failed ({e.code}): {body}") from e
        except Exception as e:
            raise VaultError(f"Vault connection failed: {e}") from e

    def health_check(self) -> bool:
        url = f"{self.addr}/v1/sys/health?standbyok=true&sealedok=true"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False


# ── Singleton pattern with runtime reload ──────────────────────────────────

_instance: VaultService | None = None


def _config_from_env() -> dict | None:
    addr = os.environ.get("VAULT_ADDR", "")
    token = os.environ.get("VAULT_TOKEN", "")
    if not addr or not token:
        return None
    return {
        "addr": addr,
        "token": token,
        "mount": os.environ.get("VAULT_MOUNT", "secret"),
        "base_path": os.environ.get("VAULT_BASE_PATH", "clustervision/users"),
        "namespace": os.environ.get("VAULT_NAMESPACE", ""),
        "enabled": True,
    }


def get_vault_service() -> VaultService | None:
    """Returns a VaultService if configured, None otherwise."""
    global _instance
    return _instance


def configure_vault(config: dict) -> VaultService:
    """Set or update the Vault configuration at runtime."""
    global _instance
    _instance = VaultService(
        addr=config["addr"],
        token=config["token"],
        mount=config.get("mount", "secret"),
        base_path=config.get("base_path", "clustervision/users"),
        namespace=config.get("namespace", ""),
    )
    logger.info("Vault configured: %s/%s", config["addr"], config.get("mount", "secret"))
    return _instance


def init_vault_from_env() -> None:
    """Called at startup — loads Vault config from env vars if present."""
    cfg = _config_from_env()
    if cfg:
        configure_vault(cfg)
        logger.info("Vault integration enabled from environment variables")
