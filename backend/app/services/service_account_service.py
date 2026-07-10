import logging
from datetime import datetime, timezone

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings
from ..core.exceptions import UserAlreadyExistsError, UserNotFoundError
from ..core.registry import RegistryMixin

logger = logging.getLogger(__name__)


class ServiceAccountService(RegistryMixin):
    def __init__(self, api_client: client.ApiClient):
        self.core_v1 = client.CoreV1Api(api_client)
        self.settings = get_settings()

    def list_users(self) -> list[dict]:
        return [u for u in self._load_registry() if u.get("type") == "service_account"]

    def get_user(self, username: str) -> dict:
        for u in self._load_registry():
            if u["name"] == username and u.get("type") == "service_account":
                return u
        raise UserNotFoundError(username)

    def _ensure_target_namespace(self, namespace: str):
        try:
            self.core_v1.read_namespace(namespace)
        except ApiException as e:
            if e.status != 404:
                raise
            try:
                self.core_v1.create_namespace(client.V1Namespace(
                    metadata=client.V1ObjectMeta(
                        name=namespace,
                        labels={"managed-by": "clustervision"},
                    )
                ))
                logger.info("Created namespace: %s", namespace)
            except ApiException as create_err:
                if create_err.status != 409:
                    raise

    def create_user(self, name: str, namespace: str = "default") -> dict:
        users = self._load_registry()
        if any(u["name"] == name and u.get("namespace") == namespace for u in users):
            raise UserAlreadyExistsError(name)

        self._ensure_target_namespace(namespace)

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

        def _append(current: list[dict]) -> list[dict]:
            if any(u["name"] == name and u.get("namespace") == namespace for u in current):
                raise UserAlreadyExistsError(name)
            return current + [user_record]

        self._update_registry(_append)
        logger.info("Created service account user: %s in %s", name, namespace)
        return user_record

    def delete_user(self, username: str, namespace: str = "default"):
        users = self._load_registry()
        matches = [
            u for u in users
            if u["name"] == username and u.get("type") == "service_account"
        ]
        if not matches:
            raise UserNotFoundError(username)

        # Same SA name can exist in several namespaces — pick the right entry,
        # and only fall back to a name-only match when it is unambiguous
        user = next((u for u in matches if u.get("namespace", "default") == namespace), None)
        if user is None:
            if len(matches) > 1:
                raise UserNotFoundError(f"{username} (namespace {namespace})")
            user = matches[0]

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

        self._update_registry(
            lambda current: [
                u for u in current
                if not (
                    u["name"] == username
                    and u.get("type") == "service_account"
                    and u.get("namespace", "default") == ns
                )
            ]
        )
        logger.info("Deleted service account user: %s in %s", username, ns)

    def import_user(self, name: str, namespace: str = "default") -> dict:
        """Register an existing ServiceAccount in the ClusterVision registry."""
        # Verify the SA actually exists in K8s
        self.core_v1.read_namespaced_service_account(name, namespace)

        now = datetime.now(timezone.utc).isoformat()
        user_record = {
            "name": name,
            "type": "service_account",
            "groups": [],
            "namespace": namespace,
            "created_at": now,
            "imported": True,
        }

        def _append(current: list[dict]) -> list[dict]:
            if any(u["name"] == name and u.get("type") == "service_account" for u in current):
                raise UserAlreadyExistsError(name)
            return current + [user_record]

        self._update_registry(_append)
        logger.info("Imported service account user: %s from %s", name, namespace)
        return user_record

    def list_unmanaged(self) -> list[dict]:
        """Return ServiceAccounts in K8s that are not in the registry."""
        registry = {
            (u["name"], u.get("namespace", "default"))
            for u in self._load_registry()
            if u.get("type") == "service_account"
        }
        # 1 call for all SAs across all namespaces (instead of 1 per namespace)
        system_namespaces = {"kube-system", "kube-public", "kube-node-lease"}
        all_sas = self.core_v1.list_service_account_for_all_namespaces()
        result = []
        for sa in all_sas.items:
            if sa.metadata.namespace in system_namespaces:
                continue
            if sa.metadata.name == "default":
                continue
            if (sa.metadata.name, sa.metadata.namespace) not in registry:
                result.append({
                    "name": sa.metadata.name,
                    "namespace": sa.metadata.namespace,
                })
        return result
