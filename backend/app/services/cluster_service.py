import base64
import json
import logging
import tempfile
import os
from typing import Optional

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from kubernetes.client.configuration import Configuration

logger = logging.getLogger(__name__)


class ClusterService:
    def __init__(self, local_core_v1: client.CoreV1Api, namespace: str, secret_name: str):
        self._core_v1 = local_core_v1
        self._namespace = namespace
        self._secret_name = secret_name
        self._clients: dict[str, client.ApiClient] = {}
        self._ca_files: dict[str, str] = {}  # cluster -> tmp file path

    # ── Registry ────────────────────────────────────────────────────────────

    def _read_configs(self) -> tuple[list[dict], Optional[str]]:
        try:
            secret = self._core_v1.read_namespaced_secret(self._secret_name, self._namespace)
            raw_b64 = (secret.data or {}).get("clusters.json")
            configs = json.loads(base64.b64decode(raw_b64).decode()) if raw_b64 else []
            return configs, secret.metadata.resource_version
        except ApiException as e:
            if e.status == 404:
                return [], None
            raise

    def _load_configs(self) -> list[dict]:
        return self._read_configs()[0]

    def _update_configs(self, mutate) -> None:
        """Atomically update the clusters secret with optimistic locking —
        retried on resourceVersion conflicts, so `mutate` must re-check its
        preconditions against its input."""
        last_exc = None
        for _ in range(5):
            configs, rv = self._read_configs()
            updated = mutate(configs)
            encoded = base64.b64encode(json.dumps(updated).encode()).decode()
            data = {"clusters.json": encoded}
            try:
                if rv is None:
                    self._core_v1.create_namespaced_secret(
                        self._namespace,
                        client.V1Secret(
                            metadata=client.V1ObjectMeta(
                                name=self._secret_name, namespace=self._namespace
                            ),
                            data=data,
                        ),
                    )
                else:
                    self._core_v1.patch_namespaced_secret(
                        self._secret_name,
                        self._namespace,
                        client.V1Secret(
                            metadata=client.V1ObjectMeta(resource_version=rv),
                            data=data,
                        ),
                    )
                return
            except ApiException as e:
                if e.status == 409:
                    last_exc = e
                    continue
                raise
        raise last_exc

    # ── CRUD ────────────────────────────────────────────────────────────────

    def list_clusters(self) -> list[dict]:
        return [
            {"name": c["name"], "api_url": c["api_url"], "is_local": False}
            for c in self._load_configs()
        ]

    def add_cluster(self, name: str, api_url: str, ca_data: str, token: str) -> dict:
        if name == "local":
            raise ValueError("'local' is reserved for the in-cluster connection")

        def _append(configs: list[dict]) -> list[dict]:
            if any(c["name"] == name for c in configs):
                raise ValueError(f"Cluster '{name}' already exists")
            return configs + [{"name": name, "api_url": api_url, "ca_data": ca_data, "token": token}]

        self._update_configs(_append)
        logger.info("Registered remote cluster: %s", name)
        return {"name": name, "api_url": api_url, "is_local": False}

    def remove_cluster(self, name: str):
        def _remove(configs: list[dict]) -> list[dict]:
            if not any(c["name"] == name for c in configs):
                raise ValueError(f"Cluster '{name}' not found")
            return [c for c in configs if c["name"] != name]

        self._update_configs(_remove)
        self._clients.pop(name, None)
        ca_file = self._ca_files.pop(name, None)
        if ca_file and os.path.exists(ca_file):
            os.unlink(ca_file)
        logger.info("Removed remote cluster: %s", name)

    # ── API client factory ──────────────────────────────────────────────────

    def get_api_client(self, name: str) -> client.ApiClient:
        if name in self._clients:
            return self._clients[name]

        configs = self._load_configs()
        cfg = next((c for c in configs if c["name"] == name), None)
        if cfg is None:
            raise ValueError(f"Cluster '{name}' not found")

        configuration = Configuration()
        configuration.host = cfg["api_url"]

        # Write CA cert to a temp file (required by urllib3)
        ca_pem = base64.b64decode(cfg["ca_data"]).decode()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"-{name}.crt", mode="w")
        tmp.write(ca_pem)
        tmp.close()
        self._ca_files[name] = tmp.name
        configuration.ssl_ca_cert = tmp.name
        configuration.verify_ssl = True

        configuration.api_key = {"authorization": cfg["token"]}
        configuration.api_key_prefix = {"authorization": "Bearer"}

        api_client = client.ApiClient(configuration)
        self._clients[name] = api_client
        logger.info("Created API client for remote cluster: %s", name)
        return api_client


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: Optional[ClusterService] = None


def get_cluster_service() -> ClusterService:
    global _instance
    if _instance is None:
        from ..core.kubernetes_client import get_local_api_client
        from ..config import get_settings
        settings = get_settings()
        local_core_v1 = client.CoreV1Api(get_local_api_client())
        _instance = ClusterService(local_core_v1, settings.registry_namespace, settings.clusters_secret)
    return _instance
