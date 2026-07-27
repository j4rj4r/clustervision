import json
import logging
import ssl
import threading
import time
import urllib.request
from functools import partial
from urllib.error import URLError

logger = logging.getLogger(__name__)


class VaultError(Exception):
    pass


class VaultNotFoundError(VaultError):
    """Secret/path not found in Vault (HTTP 404)."""


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
        # Cached from last health_check() call
        self._cached_healthy: bool = False
        self._cached_error: str | None = None

    def config_dict(self) -> dict:
        """Normalized config — used to detect changes when re-syncing."""
        return {
            "addr": self.addr,
            "token": self.token,
            "mount": self.mount,
            "base_path": self.base_path,
            "namespace": self.namespace,
            "tls_skip_verify": self.tls_skip_verify,
        }

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
            if e.code == 404:
                raise VaultNotFoundError(f"Vault {method} {path} → HTTP 404: not found")
            raise VaultError(f"Vault {method} {path} → HTTP {e.code}: {e.read().decode()}")
        except (URLError, OSError) as e:
            raise VaultError(f"Vault unreachable: {e}")

    def write_secret(self, username: str, data: dict) -> str:
        vault_path = f"{self.mount}/data/{self.base_path}/{username}"
        self._request("POST", vault_path, {"data": data})
        logger.info("Wrote private key to Vault for user %s at %s", username, vault_path)
        return vault_path

    def read_secret(self, username: str) -> dict:
        path = f"{self.mount}/data/{self.base_path}/{username}"
        result = self._request("GET", path)
        return result.get("data", {}).get("data", {})

    def health_check(self) -> tuple[bool, str | None]:
        try:
            self._request("GET", "sys/health?standbyok=true&sealedok=true&uninitok=true")
            self._cached_healthy, self._cached_error = True, None
        except VaultError as e:
            self._cached_healthy, self._cached_error = False, str(e)
        return self._cached_healthy, self._cached_error


# ── Config persistence (database) ─────────────────────────────────────────────
# The runtime Vault config must survive pod restarts AND be visible to every
# gunicorn worker/replica — an in-memory singleton alone only affects the one
# worker that handled the PUT. The `vault_config` row is the source of truth;
# each worker re-syncs from it at most every _SYNC_INTERVAL seconds.


def _read_config_row() -> dict | None:
    """None if never configured; {"enabled": False} marks an explicit runtime
    disable; anything else is a full config dict."""
    from ..db.models import VaultConfigRow
    from ..db.session import new_session
    db = new_session()
    try:
        row = db.get(VaultConfigRow, 1)
        if row is None:
            return None
        d = row.to_dict()
        return d if d.pop("enabled") else {"enabled": False}
    finally:
        db.close()


def _write_config_row(cfg: dict) -> None:
    from ..db.models import VaultConfigRow
    from ..db.session import new_session
    db = new_session()
    try:
        row = db.get(VaultConfigRow, 1)
        if row is None:
            row = VaultConfigRow(id=1)
            db.add(row)
        row.enabled = cfg.get("enabled", True) is not False
        row.addr = cfg.get("addr", "")
        row.token = cfg.get("token", "")
        row.mount = cfg.get("mount", "secret")
        row.base_path = cfg.get("base_path", "clustervision/users")
        row.namespace = cfg.get("namespace", "")
        row.tls_skip_verify = bool(cfg.get("tls_skip_verify", False))
        db.commit()
    finally:
        db.close()


# ── Singleton, synchronized across workers via the config row ─────────────

_vault_svc: VaultService | None = None
_lock = threading.Lock()
_last_sync = 0.0
_SYNC_INTERVAL = 30.0


def _env_config() -> dict | None:
    from ..config import get_settings
    s = get_settings()
    if s.vault_enabled and s.vault_addr and s.vault_token:
        return {
            "addr": s.vault_addr,
            "token": s.vault_token,
            "mount": s.vault_mount,
            "base_path": s.vault_base_path,
            "namespace": s.vault_namespace,
            "tls_skip_verify": s.vault_tls_skip_verify,
        }
    return None


def _apply_config(cfg: dict | None) -> None:
    global _vault_svc
    if not cfg or cfg.get("enabled") is False:
        if _vault_svc is not None:
            logger.info("Vault integration disabled")
        _vault_svc = None
        return
    candidate = VaultService(
        addr=cfg.get("addr", ""),
        token=cfg.get("token", ""),
        mount=cfg.get("mount", "secret"),
        base_path=cfg.get("base_path", "clustervision/users"),
        namespace=cfg.get("namespace", ""),
        tls_skip_verify=bool(cfg.get("tls_skip_verify", False)),
    )
    if not candidate.addr or not candidate.token:
        _vault_svc = None
        return
    # Keep the existing instance (and its cached health) if nothing changed
    if _vault_svc is None or _vault_svc.config_dict() != candidate.config_dict():
        _vault_svc = candidate
        logger.info("Vault configuration (re)loaded")


def _sync(force: bool = False) -> None:
    """Re-read the config row so this worker converges on the shared state.
    Blocking (K8s read) — must run in a thread, not on the event loop."""
    global _last_sync
    now = time.monotonic()
    if not force and now - _last_sync < _SYNC_INTERVAL:
        return
    _last_sync = now
    try:
        cfg = _read_config_row()
    except Exception as e:
        logger.warning("Could not read Vault config: %s", e)
        # Keep the current state; bootstrap from env if we have nothing yet
        if _vault_svc is None:
            _apply_config(_env_config())
        return
    _apply_config(cfg if cfg is not None else _env_config())


def get_vault_service() -> VaultService | None:
    """May block on a K8s read (at most once per _SYNC_INTERVAL) — call via
    run_sync from async code."""
    with _lock:
        _sync()
    return _vault_svc


def configure_vault(addr: str, token: str, mount: str, base_path: str, namespace: str, tls_skip_verify: bool = False) -> VaultService:
    global _last_sync
    cfg = {
        "addr": addr,
        "token": token,
        "mount": mount,
        "base_path": base_path,
        "namespace": namespace,
        "tls_skip_verify": tls_skip_verify,
    }
    with _lock:
        _write_config_row(cfg)  # persist first — other workers pick it up
        _apply_config(cfg)
        _last_sync = time.monotonic()
    return _vault_svc


def disable_vault():
    global _vault_svc, _last_sync
    with _lock:
        # Explicit marker: an absent Secret would fall back to the env config
        _write_config_row({"enabled": False})
        _vault_svc = None
        _last_sync = time.monotonic()


async def init_vault_from_env():
    """Startup: prefer the persisted runtime config, fall back to env vars."""
    from ..core.async_utils import run_sync
    await run_sync(partial(_sync, True))
    svc = _vault_svc
    if svc:
        healthy, _ = await run_sync(svc.health_check)
        logger.info("Vault integration initialized (healthy=%s)", healthy)
