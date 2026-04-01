import base64
import logging

import yaml
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings

logger = logging.getLogger(__name__)


class KubeconfigService:
    def __init__(self, api_client: client.ApiClient):
        self.core_v1 = client.CoreV1Api(api_client)
        self.version_api = client.VersionApi(api_client)
        self.settings = get_settings()
        self._ca_cache: str | None = None
        self._api_url_cache: str | None = None

    def generate_for_cert_user(
        self,
        username: str,
        certificate_pem: str,
        private_key_pem: str,
        namespace: str = "default",
    ) -> str:
        ca_data = self._get_cluster_ca()
        api_url = self._get_api_server_url()
        cluster_name = self.settings.cluster_name

        kubeconfig = {
            "apiVersion": "v1",
            "kind": "Config",
            "preferences": {},
            "clusters": [
                {
                    "name": cluster_name,
                    "cluster": {
                        "server": api_url,
                        "certificate-authority-data": ca_data,
                    },
                }
            ],
            "contexts": [
                {
                    "name": f"{username}@{cluster_name}",
                    "context": {
                        "cluster": cluster_name,
                        "user": username,
                        **({"namespace": namespace} if namespace else {}),
                    },
                }
            ],
            "current-context": f"{username}@{cluster_name}",
            "users": [
                {
                    "name": username,
                    "user": {
                        "client-certificate-data": base64.b64encode(
                            certificate_pem.encode()
                        ).decode(),
                        "client-key-data": base64.b64encode(
                            private_key_pem.encode()
                        ).decode(),
                    },
                }
            ],
        }
        return yaml.dump(kubeconfig, default_flow_style=False, allow_unicode=True)

    def generate_for_service_account(
        self,
        sa_name: str,
        sa_namespace: str,
        target_namespace: str = "default",
    ) -> str:
        token = self._get_sa_token(sa_name, sa_namespace)
        ca_data = self._get_cluster_ca()
        api_url = self._get_api_server_url()
        cluster_name = self.settings.cluster_name

        kubeconfig = {
            "apiVersion": "v1",
            "kind": "Config",
            "preferences": {},
            "clusters": [
                {
                    "name": cluster_name,
                    "cluster": {
                        "server": api_url,
                        "certificate-authority-data": ca_data,
                    },
                }
            ],
            "contexts": [
                {
                    "name": f"{sa_name}@{cluster_name}",
                    "context": {
                        "cluster": cluster_name,
                        "user": sa_name,
                        **({"namespace": target_namespace} if target_namespace else {}),
                    },
                }
            ],
            "current-context": f"{sa_name}@{cluster_name}",
            "users": [
                {
                    "name": sa_name,
                    "user": {"token": token},
                }
            ],
        }
        return yaml.dump(kubeconfig, default_flow_style=False, allow_unicode=True)

    def _get_cluster_ca(self) -> str:
        if self._ca_cache is not None:
            return self._ca_cache
        try:
            cm = self.core_v1.read_namespaced_config_map("kube-root-ca.crt", "kube-system")
            ca_pem = cm.data.get("ca.crt", "")
            self._ca_cache = base64.b64encode(ca_pem.encode()).decode()
        except ApiException:
            try:
                with open("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt", "rb") as f:
                    self._ca_cache = base64.b64encode(f.read()).decode()
            except FileNotFoundError:
                self._ca_cache = ""
        return self._ca_cache

    def _get_api_server_url(self) -> str:
        if self._api_url_cache is not None:
            return self._api_url_cache
        if self.settings.cluster_api_url:
            self._api_url_cache = self.settings.cluster_api_url
        else:
            try:
                with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace"):
                    self._api_url_cache = "https://kubernetes.default.svc"
            except FileNotFoundError:
                from kubernetes import config as k8s_config
                cfg = k8s_config.kube_config.list_kube_config_contexts()
                for ctx in cfg[0]:
                    if ctx.get("name") == cfg[1].get("name"):
                        cluster_name = ctx.get("context", {}).get("cluster")
                        self._api_url_cache = f"https://{cluster_name}"
                        break
                else:
                    self._api_url_cache = "https://kubernetes.default.svc"
        return self._api_url_cache

    def _get_sa_token(self, sa_name: str, namespace: str) -> str:
        # Prefer a long-lived service-account-token secret if one exists
        secrets = self.core_v1.list_namespaced_secret(
            namespace,
            label_selector=f"kubernetes.io/service-account.name={sa_name}",
        )
        for secret in secrets.items:
            if secret.type != "kubernetes.io/service-account-token":
                continue
            token_bytes = (secret.data or {}).get("token")
            if token_bytes:
                return base64.b64decode(token_bytes).decode()

        # Fallback: generate an ephemeral token via TokenRequest API
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
