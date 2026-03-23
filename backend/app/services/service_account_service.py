import json
import logging
from datetime import datetime, timezone

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings
from ..core.exceptions import UserAlreadyExistsError, UserNotFoundError

logger = logging.getLogger(__name__)


class ServiceAccountService:
    def __init__(self, api_client: client.ApiClient):
        self.core_v1 = client.CoreV1Api(api_client)
        self.settings = get_settings()

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

    def list_users(self) -> list[dict]:
        return [u for u in self._load_registry() if u.get("type") == "service_account"]

    def get_user(self, username: str, namespace: str = "default") -> dict:
        for u in self._load_registry():
            if u["name"] == username and u.get("type") == "service_account":
                return u
        raise UserNotFoundError(username)

    def create_user(self, name: str, namespace: str = "default") -> dict:
        users = self._load_registry()
        if any(u["name"] == name and u.get("namespace") == namespace for u in users):
            raise UserAlreadyExistsError(name)

        # Create the ServiceAccount
        sa = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={"managed-by": "clustervision"},
            )
        )
        try:
            self.core_v1.create_namespaced_service_account(namespace, sa)
        except ApiException as e:
            if e.status != 409:
                raise

        # Create a long-lived token secret (K8s 1.24+)
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=f"clustervision-{name}-token",
                namespace=namespace,
                annotations={"kubernetes.io/service-account.name": name},
                labels={"managed-by": "clustervision"},
            ),
            type="kubernetes.io/service-account-token",
        )
        try:
            self.core_v1.create_namespaced_secret(namespace, secret)
        except ApiException as e:
            if e.status != 409:
                raise

        now = datetime.now(timezone.utc).isoformat()
        user_record = {
            "name": name,
            "type": "service_account",
            "groups": [],
            "namespace": namespace,
            "created_at": now,
        }
        users.append(user_record)
        self._save_registry(users)
        logger.info(f"Created service account user: {name} in {namespace}")
        return user_record

    def delete_user(self, username: str, namespace: str = "default"):
        users = self._load_registry()
        user = next(
            (u for u in users if u["name"] == username and u.get("type") == "service_account"),
            None,
        )
        if not user:
            raise UserNotFoundError(username)

        ns = user.get("namespace", namespace)
        try:
            self.core_v1.delete_namespaced_service_account(username, ns)
        except ApiException as e:
            if e.status != 404:
                raise

        try:
            self.core_v1.delete_namespaced_secret(f"clustervision-{username}-token", ns)
        except ApiException as e:
            if e.status != 404:
                raise

        updated = [
            u for u in users
            if not (u["name"] == username and u.get("type") == "service_account")
        ]
        self._save_registry(updated)
        logger.info(f"Deleted service account user: {username}")

    def get_token(self, sa_name: str, namespace: str) -> str:
        """Get the token for a ServiceAccount using the TokenRequest API."""
        token_request = client.AuthenticationV1TokenRequest(
            spec=client.V1TokenRequestSpec(
                audiences=["https://kubernetes.default.svc"],
                expiration_seconds=86400 * 365,
            )
        )
        resp = self.core_v1.create_namespaced_service_account_token(
            sa_name, namespace, token_request
        )
        return resp.status.token
