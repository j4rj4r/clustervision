import json
from collections.abc import Callable

from kubernetes import client
from kubernetes.client.exceptions import ApiException

_MAX_CONFLICT_RETRIES = 5


class RegistryMixin:
    """ConfigMap-backed user registry.

    Requires subclasses to expose:
      - self.core_v1  : client.CoreV1Api
      - self.settings : Settings
    """

    def _ensure_namespace(self):
        try:
            self.core_v1.read_namespace(self.settings.registry_namespace)
        except ApiException as e:
            if e.status == 404:
                self.core_v1.create_namespace(
                    client.V1Namespace(
                        metadata=client.V1ObjectMeta(name=self.settings.registry_namespace)
                    )
                )

    def _read_registry(self) -> tuple[list[dict], str | None]:
        """Return (users, resourceVersion) — resourceVersion is None if the
        ConfigMap does not exist yet."""
        try:
            cm = self.core_v1.read_namespaced_config_map(
                self.settings.registry_configmap,
                self.settings.registry_namespace,
            )
            users = json.loads((cm.data or {}).get("users.json", "[]"))
            return users, cm.metadata.resource_version
        except ApiException as e:
            if e.status == 404:
                return [], None
            raise

    def _load_registry(self) -> list[dict]:
        return self._read_registry()[0]

    def _update_registry(self, mutate: Callable[[list[dict]], list[dict]]) -> list[dict]:
        """Atomically update the registry with optimistic locking.

        `mutate` receives the freshly-loaded user list and returns the new one.
        On a resourceVersion conflict (concurrent writer) the load+mutate+write
        cycle is retried, so `mutate` must be safe to re-run and should perform
        its own consistency checks (duplicates, existence) against its input.
        """
        last_exc: ApiException | None = None
        for _ in range(_MAX_CONFLICT_RETRIES):
            users, rv = self._read_registry()
            updated = mutate(users)
            data = {"users.json": json.dumps(updated, indent=2)}
            try:
                if rv is None:
                    self._ensure_namespace()
                    self.core_v1.create_namespaced_config_map(
                        self.settings.registry_namespace,
                        client.V1ConfigMap(
                            metadata=client.V1ObjectMeta(
                                name=self.settings.registry_configmap,
                                namespace=self.settings.registry_namespace,
                            ),
                            data=data,
                        ),
                    )
                else:
                    self.core_v1.patch_namespaced_config_map(
                        self.settings.registry_configmap,
                        self.settings.registry_namespace,
                        client.V1ConfigMap(
                            metadata=client.V1ObjectMeta(resource_version=rv),
                            data=data,
                        ),
                    )
                return updated
            except ApiException as e:
                # 409 = conflict: either the resourceVersion changed under us
                # or the ConfigMap was created concurrently — reload and retry
                if e.status == 409:
                    last_exc = e
                    continue
                raise
        raise last_exc
