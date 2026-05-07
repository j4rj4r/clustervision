import json
import logging
import ssl
import urllib.request
from urllib.error import URLError

logger = logging.getLogger(__name__)


class VaultError(Exception):
    pass


class VaultService:
    def __init__(self, addr: str, token: str, mount: str = "secret", base_path: str = "clustervision/users", namespace: str = "", tls_skip_verify: bool = False):
        self.addr = addr.rstrip("/")
        self.token = token
        self.mount = mount.strip("/")
        self.base_path = base_path.strip("/")
        self.namespace = namespace
        self.tls_skip_verify = tls_skip_verify
        self._ctx = ssl.create_default_context()
        if tls_skip_verify:
            self._ctx.check_hostname = False
            self._ctx.verify_mode = ssl.CERT_NONE

    def _headers(self) -> dict:
        h = {"X-Vault-Token": self.token, "Content-Type": "application/json"}
        if self.namespace:
            h["X-Vault-Namespace"] = self.namespace
        return h

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self.addr}/v1/{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers())
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=5) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise VaultError(f"Vault {method} {path} → HTTP {e.code}: {e.read().decode()}")
        except (URLError, OSError) as e:
            raise VaultError(f"Vault unreachable: {e}")

    def write_secret(self, username: str, data: dict) -> str:
        path = f"{self.mount}/data/{self.base_path}/{username}"
        self._request("POST", path, {"data": data})
        vault_path = f"{self.mount}/data/{self.base_path}/{username}"
        logger.info("Wrote private key to Vault for user %s at %s", username, vault_path)
        return vault_path

    def read_secret(self, username: str) -> dict:
        path = f"{self.mount}/data/{self.base_path}/{username}"
        result = self._request("GET", path)
        return result.get("data", {}).get("data", {})

    def health_check(self) -> tuple[bool, str | None]:
        try:
            self._request("GET", "sys/health?standbyok=true&sealedok=true&uninitok=true")
            return True, None
        except VaultError as e:
            return False, str(e)


# ── Singleton ──────────────────────────────────────────────────────────────

_vault_svc: VaultService | None = None


def get_vault_service() -> VaultService | None:
    return _vault_svc


def configure_vault(addr: str, token: str, mount: str, base_path: str, namespace: str, tls_skip_verify: bool = False) -> VaultService:
    global _vault_svc
    _vault_svc = VaultService(addr=addr, token=token, mount=mount, base_path=base_path, namespace=namespace, tls_skip_verify=tls_skip_verify)
    return _vault_svc


def disable_vault():
    global _vault_svc
    _vault_svc = None


def init_vault_from_env():
    from ..config import get_settings
    s = get_settings()
    if s.vault_enabled and s.vault_addr and s.vault_token:
        configure_vault(
            addr=s.vault_addr,
            token=s.vault_token,
            mount=s.vault_mount,
            base_path=s.vault_base_path,
            namespace=s.vault_namespace,
            tls_skip_verify=s.vault_tls_skip_verify,
        )
        logger.info("Vault integration initialized from environment")
