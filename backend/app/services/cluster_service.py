import base64
import logging
import os
import tempfile
import threading
import time

from kubernetes import client
from kubernetes.client.configuration import Configuration
from kubernetes.client.exceptions import ApiException
from sqlalchemy import select

from ..db.models import RegisteredCluster
from ..db.session import new_session

logger = logging.getLogger(__name__)

# How long a cached API client is trusted before re-checking the stored config
# — credentials may have been rotated through another worker/replica
_RELOAD_INTERVAL = 30.0


class ClusterConnectionError(Exception):
    """The cluster API could not be reached with the provided credentials."""


class ClusterService:
    def __init__(self):
        self._clients: dict[str, client.ApiClient] = {}
        self._client_cfgs: dict[str, dict] = {}  # config each cached client was built from
        self._ca_files: dict[str, str] = {}  # cluster -> tmp file path
        self._cache_lock = threading.Lock()
        self._last_reload = 0.0

    # ── Registry ────────────────────────────────────────────────────────────
    # ClusterService is a long-lived singleton (not request-scoped), so each
    # call opens and closes its own short-lived DB session rather than holding
    # one for the process lifetime.

    def _load_configs(self) -> list[dict]:
        db = new_session()
        try:
            return [c.to_dict() for c in db.scalars(select(RegisteredCluster))]
        finally:
            db.close()

    def _update_configs(self, mutate) -> None:
        """Replace the registry with `mutate(current)` — same contract as
        before, so callers' own consistency checks (duplicates, existence)
        against the input still apply."""
        db = new_session()
        try:
            before = {c["name"]: c for c in self._load_configs()}
            after_list = mutate(list(before.values()))
            after = {c["name"]: c for c in after_list}

            for name in before.keys() - after.keys():
                existing = db.get(RegisteredCluster, name)
                if existing is not None:
                    db.delete(existing)

            for name, cfg in after.items():
                existing = db.get(RegisteredCluster, name)
                if existing is None:
                    db.add(RegisteredCluster(name=name, api_url=cfg["api_url"], ca_data=cfg["ca_data"], token=cfg["token"]))
                elif before.get(name) != cfg:
                    existing.api_url = cfg["api_url"]
                    existing.ca_data = cfg["ca_data"]
                    existing.token = cfg["token"]

            db.commit()
        finally:
            db.close()

    # ── CRUD ────────────────────────────────────────────────────────────────

    def list_clusters(self) -> list[dict]:
        return [
            {"name": c["name"], "api_url": c["api_url"], "is_local": False}
            for c in self._load_configs()
        ]

    def add_cluster(self, name: str, api_url: str, ca_data: str, token: str) -> dict:
        if name == "local":
            raise ValueError("'local' is reserved for the in-cluster connection")

        # Reject broken credentials at registration time — otherwise the
        # failure only surfaces when someone switches to the cluster
        self.verify_connectivity(name, api_url, ca_data, token)

        def _append(configs: list[dict]) -> list[dict]:
            if any(c["name"] == name for c in configs):
                raise ValueError(f"Cluster '{name}' already exists")
            return [*configs, {"name": name, "api_url": api_url, "ca_data": ca_data, "token": token}]

        self._update_configs(_append)
        logger.info("Registered remote cluster: %s", name)
        return {"name": name, "api_url": api_url, "is_local": False}

    def remove_cluster(self, name: str):
        def _remove(configs: list[dict]) -> list[dict]:
            if not any(c["name"] == name for c in configs):
                raise ValueError(f"Cluster '{name}' not found")
            return [c for c in configs if c["name"] != name]

        self._update_configs(_remove)
        with self._cache_lock:
            self._drop_client(name)
        logger.info("Removed remote cluster: %s", name)

    # ── API client factory ──────────────────────────────────────────────────

    @staticmethod
    def _connection_cfg(cfg: dict) -> dict:
        return {k: cfg[k] for k in ("api_url", "ca_data", "token")}

    def _drop_client(self, name: str) -> None:
        """Must be called with _cache_lock held."""
        old = self._clients.pop(name, None)
        self._client_cfgs.pop(name, None)
        if old is not None:
            try:
                old.close()
            except Exception as e:
                logger.debug("Error closing stale API client for %s: %s", name, e)
        ca_file = self._ca_files.pop(name, None)
        if ca_file and os.path.exists(ca_file):
            os.unlink(ca_file)

    def _build_client(self, name: str, cfg: dict) -> client.ApiClient:
        configuration = Configuration()
        configuration.host = cfg["api_url"]

        # Write CA cert to a temp file (required by urllib3)
        ca_pem = base64.b64decode(cfg["ca_data"]).decode()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"-{name}.crt", mode="w") as tmp:
            tmp.write(ca_pem)
        self._ca_files[name] = tmp.name
        configuration.ssl_ca_cert = tmp.name
        configuration.verify_ssl = True

        configuration.api_key = {"authorization": cfg["token"]}
        configuration.api_key_prefix = {"authorization": "Bearer"}
        return client.ApiClient(configuration)

    def get_api_client(self, name: str) -> client.ApiClient:
        with self._cache_lock:
            cached = self._clients.get(name)
            if cached is not None and time.monotonic() - self._last_reload < _RELOAD_INTERVAL:
                return cached

            # Cache miss or revalidation window elapsed — re-read the stored
            # configs so credential changes made by other workers are picked up
            configs = self._load_configs()
            self._last_reload = time.monotonic()
            cfg = next((c for c in configs if c["name"] == name), None)
            if cfg is None:
                self._drop_client(name)
                raise ValueError(f"Cluster '{name}' not found")

            wanted = self._connection_cfg(cfg)
            if cached is not None:
                if self._client_cfgs.get(name) == wanted:
                    return cached
                self._drop_client(name)

            api_client = self._build_client(name, wanted)
            self._clients[name] = api_client
            self._client_cfgs[name] = wanted
            logger.info("Created API client for remote cluster: %s", name)
            return api_client

    def verify_connectivity(self, name: str, api_url: str, ca_data: str, token: str) -> None:
        """Probe /version with the given credentials, raising
        ClusterConnectionError if the API server is unreachable or rejects them."""
        probe_key = f"__verify__{name}"
        try:
            with self._cache_lock:
                api_client = self._build_client(probe_key, self._connection_cfg(
                    {"api_url": api_url, "ca_data": ca_data, "token": token}
                ))
        except Exception as e:
            raise ClusterConnectionError(f"Invalid CA certificate data: {e}")
        try:
            client.VersionApi(api_client).get_code(_request_timeout=5)
        except ApiException as e:
            raise ClusterConnectionError(
                f"Cluster API at {api_url} rejected the credentials: HTTP {e.status} {e.reason}"
            )
        except Exception as e:
            raise ClusterConnectionError(f"Cannot reach cluster API at {api_url}: {e}")
        finally:
            api_client.close()
            with self._cache_lock:
                ca_file = self._ca_files.pop(probe_key, None)
            if ca_file and os.path.exists(ca_file):
                os.unlink(ca_file)


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: ClusterService | None = None


def get_cluster_service() -> ClusterService:
    global _instance
    if _instance is None:
        _instance = ClusterService()
    return _instance
