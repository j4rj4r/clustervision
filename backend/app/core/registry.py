import json
from kubernetes import client
from kubernetes.client.exceptions import ApiException


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

    def _load_registry(self) -> list[dict]:
        try:
            cm = self.core_v1.read_namespaced_config_map(
                self.settings.registry_configmap,
                self.settings.registry_namespace,
            )
            return json.loads(cm.data.get("users.json", "[]"))
        except ApiException as e:
            if e.status == 404:
                return []
            raise

    def _save_registry(self, users: list[dict]):
        self._ensure_namespace()
        data = {"users.json": json.dumps(users, indent=2)}
        try:
            self.core_v1.patch_namespaced_config_map(
                self.settings.registry_configmap,
                self.settings.registry_namespace,
                client.V1ConfigMap(data=data),
            )
        except ApiException as e:
            if e.status == 404:
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
                raise
