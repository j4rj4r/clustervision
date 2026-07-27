import base64
import logging
import time
from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from sqlalchemy.orm import Session

from ..core.exceptions import (
    CertificateTimeoutError,
    ImportedUserError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..core.registry import RegistryMixin

logger = logging.getLogger(__name__)

REGISTRY_ANNOTATION = "clustervision.io/managed"


class CertificateService(RegistryMixin):
    def __init__(self, api_client: client.ApiClient, db: Session):
        self.certs_api = client.CertificatesV1Api(api_client)
        self.core_v1 = client.CoreV1Api(api_client)
        self.db = db

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

        # Step 4: Approve the CSR — mutate the existing object and PUT it back
        existing_csr = self.certs_api.read_certificate_signing_request(csr_name)
        existing_csr.status = client.V1CertificateSigningRequestStatus(
            conditions=[
                client.V1CertificateSigningRequestCondition(
                    type="Approved",
                    status="True",
                    reason="ClusterVisionApproval",
                    message=f"Approved by ClusterVision for user {username}",
                    last_update_time=datetime.now(UTC),
                )
            ]
        )
        self.certs_api.replace_certificate_signing_request_approval(csr_name, existing_csr)

        # Step 5: Wait for signed certificate
        signed_cert_b64 = self._wait_for_certificate(csr_name)
        certificate_pem = base64.b64decode(signed_cert_b64).decode()

        private_key_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        # Step 6: Build the registry record
        # Read the expiry from the signed certificate — the API server may cap
        # the requested duration (--cluster-signing-duration)
        signed_cert = x509.load_pem_x509_certificate(certificate_pem.encode())
        now = datetime.now(UTC).isoformat()
        expiry = signed_cert.not_valid_after_utc.isoformat()
        user_record = {
            "name": username,
            "type": "certificate",
            "groups": groups,
            "namespace": "default",
            "csr_name": csr_name,
            "created_at": now,
            "cert_expiry": expiry,
        }

        # Step 7: Store private key in Vault BEFORE registering the user.
        # If Vault is enabled, the key must never be returned inline — on a
        # write failure we roll back the CSR and fail loudly instead of
        # silently downgrading to inline delivery.
        from .vault_service import get_vault_service
        vault_svc = get_vault_service()
        vault_path = None
        if vault_svc:
            try:
                vault_path = vault_svc.write_secret(username, {
                    "private_key_pem": private_key_pem,
                    "certificate_pem": certificate_pem,
                })
            except Exception as e:
                logger.error("Vault write failed for %s — rolling back CSR: %s", username, e)
                try:
                    self.certs_api.delete_certificate_signing_request(csr_name)
                except ApiException:
                    logger.warning("Could not clean up CSR %s after Vault failure", csr_name)
                raise HTTPException(
                    status_code=502,
                    detail=f"Vault is enabled but the private key could not be stored: {e}",
                )

        # Step 8: Save to registry
        def _append(current: list[dict]) -> list[dict]:
            if any(u["name"] == username for u in current):
                raise UserAlreadyExistsError(username)
            return [*current, user_record]

        self._update_registry(_append)
        logger.info("Created certificate user: %s", username)

        if vault_path:
            return {**user_record, "vault_path": vault_path, "certificate_pem": certificate_pem}
        return {**user_record, "private_key_pem": private_key_pem, "certificate_pem": certificate_pem}

    def delete_user(self, username: str):
        users = self._load_registry()
        user = next((u for u in users if u["name"] == username and u.get("type") == "certificate"), None)
        if not user:
            raise UserNotFoundError(username)

        # Delete CSR (imported users have none)
        if user.get("csr_name"):
            try:
                self.certs_api.delete_certificate_signing_request(user["csr_name"])
            except ApiException as e:
                if e.status != 404:
                    raise

        # Remove from registry
        self._update_registry(
            lambda current: [
                u for u in current
                if not (u["name"] == username and u.get("type") == "certificate")
            ]
        )
        logger.info("Deleted certificate user: %s", username)

    def import_user(self, username: str, groups: list[str]) -> dict:
        """Register an existing certificate user in the registry (no CSR created)."""
        now = datetime.now(UTC).isoformat()
        user_record = {
            "name": username,
            "type": "certificate",
            "groups": groups,
            "namespace": "default",
            "created_at": now,
            "imported": True,
        }

        def _append(current: list[dict]) -> list[dict]:
            if any(u["name"] == username for u in current):
                raise UserAlreadyExistsError(username)
            return [*current, user_record]

        self._update_registry(_append)
        logger.info("Imported certificate user: %s", username)
        return user_record

    def get_certificate_pem(self, username: str) -> str:
        user = self.get_user(username)
        if user.get("imported") or not user.get("csr_name"):
            raise ImportedUserError(
                f"User '{username}' was imported and has no managed CSR. "
                "Provide the certificate PEM directly."
            )
        csr = self.certs_api.read_certificate_signing_request(user["csr_name"])
        if not csr.status.certificate:
            raise ImportedUserError(f"No signed certificate found for user {username}")
        return base64.b64decode(csr.status.certificate).decode()

    def _wait_for_certificate(self, csr_name: str, timeout: int = 30) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            csr = self.certs_api.read_certificate_signing_request(csr_name)
            if csr.status and csr.status.certificate:
                return csr.status.certificate
            time.sleep(1)
        raise CertificateTimeoutError(csr_name)
