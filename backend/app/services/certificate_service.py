import base64
import json
import time
import logging
from datetime import datetime, timezone, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings
from ..core.exceptions import CertificateTimeoutError, UserAlreadyExistsError, UserNotFoundError

logger = logging.getLogger(__name__)

REGISTRY_ANNOTATION = "clustervision.io/managed"


class CertificateService:
    def __init__(self, api_client: client.ApiClient):
        self.certs_api = client.CertificatesV1Api(api_client)
        self.core_v1 = client.CoreV1Api(api_client)
        self.settings = get_settings()

    # ── User registry (ConfigMap-backed) ───────────────────────────────────

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

    # ── Public API ──────────────────────────────────────────────────────────

    def list_users(self) -> list[dict]:
        return [u for u in self._load_registry() if u.get("type") == "certificate"]

    def get_user(self, username: str) -> dict:
        for u in self._load_registry():
            if u["name"] == username and u.get("type") == "certificate":
                return u
        raise UserNotFoundError(username)

    def create_user(self, username: str, groups: list[str]) -> dict:
        users = self._load_registry()
        if any(u["name"] == username for u in users):
            raise UserAlreadyExistsError(username)

        # Step 1+2: Generate private key and CSR
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, username)]
        for group in groups:
            name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, group))

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name(name_attrs))
            .sign(private_key, hashes.SHA256())
        )
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)

        # Step 3: Create K8s CSR object
        csr_name = f"clustervision:{username}"
        k8s_csr = client.V1CertificateSigningRequest(
            metadata=client.V1ObjectMeta(name=csr_name),
            spec=client.V1CertificateSigningRequestSpec(
                request=base64.b64encode(csr_pem).decode(),
                signer_name="kubernetes.io/kube-apiserver-client",
                usages=["client auth"],
                expiration_seconds=86400 * 365,
            ),
        )
        try:
            self.certs_api.create_certificate_signing_request(k8s_csr)
        except ApiException as e:
            if e.status == 409:
                # CSR exists from a previous incomplete creation — delete and retry
                self.certs_api.delete_certificate_signing_request(csr_name)
                time.sleep(1)
                self.certs_api.create_certificate_signing_request(k8s_csr)
            else:
                raise

        # Step 4: Approve the CSR
        approval = client.V1CertificateSigningRequest(
            status=client.V1CertificateSigningRequestStatus(
                conditions=[
                    client.V1CertificateSigningRequestCondition(
                        type="Approved",
                        status="True",
                        reason="ClusterVisionApproval",
                        message=f"Approved by ClusterVision for user {username}",
                    )
                ]
            )
        )
        self.certs_api.patch_certificate_signing_request_approval(csr_name, approval)

        # Step 5: Wait for signed certificate
        signed_cert_b64 = self._wait_for_certificate(csr_name)
        certificate_pem = base64.b64decode(signed_cert_b64).decode()

        private_key_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        # Step 6: Save to registry
        now = datetime.now(timezone.utc).isoformat()
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        user_record = {
            "name": username,
            "type": "certificate",
            "groups": groups,
            "namespace": "default",
            "csr_name": csr_name,
            "created_at": now,
            "cert_expiry": expiry,
        }
        users.append(user_record)
        self._save_registry(users)
        logger.info(f"Created certificate user: {username}")

        return {**user_record, "private_key_pem": private_key_pem, "certificate_pem": certificate_pem}

    def delete_user(self, username: str):
        users = self._load_registry()
        user = next((u for u in users if u["name"] == username and u.get("type") == "certificate"), None)
        if not user:
            raise UserNotFoundError(username)

        # Delete CSR
        try:
            self.certs_api.delete_certificate_signing_request(user["csr_name"])
        except ApiException as e:
            if e.status != 404:
                raise

        # Remove from registry
        updated = [u for u in users if not (u["name"] == username and u.get("type") == "certificate")]
        self._save_registry(updated)
        logger.info(f"Deleted certificate user: {username}")

    def get_certificate_pem(self, username: str) -> str:
        user = self.get_user(username)
        csr = self.certs_api.read_certificate_signing_request(user["csr_name"])
        if not csr.status.certificate:
            raise ValueError(f"No signed certificate found for user {username}")
        return base64.b64decode(csr.status.certificate).decode()

    def _wait_for_certificate(self, csr_name: str, timeout: int = 30) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            csr = self.certs_api.read_certificate_signing_request(csr_name)
            if csr.status and csr.status.certificate:
                return csr.status.certificate
            time.sleep(1)
        raise CertificateTimeoutError(csr_name)
