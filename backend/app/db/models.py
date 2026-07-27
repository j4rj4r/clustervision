import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AccessRequestRecord(Base):
    __tablename__ = "access_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester: Mapped[str] = mapped_column(String(253), index=True)
    target_username: Mapped[str] = mapped_column(String(253))
    user_kind: Mapped[str] = mapped_column(String(32))
    sa_namespace: Mapped[str | None] = mapped_column(String(63), nullable=True)
    role_name: Mapped[str] = mapped_column(String(253))
    role_kind: Mapped[str] = mapped_column(String(32))
    namespace: Mapped[str | None] = mapped_column(String(63), nullable=True)
    ttl_minutes: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(253), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    binding_name: Mapped[str | None] = mapped_column(String(253), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requester": self.requester,
            "target_username": self.target_username,
            "user_kind": self.user_kind,
            "sa_namespace": self.sa_namespace,
            "role_name": self.role_name,
            "role_kind": self.role_kind,
            "namespace": self.namespace,
            "ttl_minutes": self.ttl_minutes,
            "reason": self.reason,
            "status": self.status,
            "requested_at": self.requested_at.isoformat(),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "binding_name": self.binding_name,
        }


class LocalUser(Base):
    """ClusterVision's own login accounts (admin/viewer) — independent from the
    Kubernetes-managed users tracked in ManagedUser."""

    __tablename__ = "local_users"

    username: Mapped[str] = mapped_column(String(253), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))


class ManagedUser(Base):
    """Registry of Kubernetes users ClusterVision manages — certificate (X.509)
    or ServiceAccount. Shared table for both, distinguished by `type`, mirroring
    the single ConfigMap this replaces."""

    __tablename__ = "managed_users"

    # (name, namespace) was the uniqueness key in the ConfigMap version — a
    # certificate user's namespace is always "default", so this also lets two
    # ServiceAccounts of the same name coexist in different namespaces.
    name: Mapped[str] = mapped_column(String(253), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(63), primary_key=True, default="default")
    type: Mapped[str] = mapped_column(String(32))  # "certificate" | "service_account"
    groups_csv: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    csr_name: Mapped[str | None] = mapped_column(String(253), nullable=True)
    cert_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "type": self.type,
            "groups": [g for g in self.groups_csv.split(",") if g],
            "namespace": self.namespace,
            "created_at": self.created_at.isoformat(),
        }
        if self.csr_name:
            d["csr_name"] = self.csr_name
        if self.cert_expiry:
            d["cert_expiry"] = self.cert_expiry.isoformat()
        if self.imported:
            d["imported"] = True
        return d


class TokenHistoryEntry(Base):
    __tablename__ = "token_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user: Mapped[str] = mapped_column(String(253))
    user_type: Mapped[str] = mapped_column(String(32))
    namespace: Mapped[str] = mapped_column(String(63))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user": self.user,
            "user_type": self.user_type,
            "namespace": self.namespace,
            "generated_at": self.generated_at.isoformat(),
        }


class RegisteredCluster(Base):
    """Remote cluster registry — holds live credential material (a bearer
    token and CA cert per cluster), same sensitivity as the Secret it replaces."""

    __tablename__ = "registered_clusters"

    name: Mapped[str] = mapped_column(String(63), primary_key=True)
    api_url: Mapped[str] = mapped_column(String(500))
    ca_data: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)

    def to_dict(self) -> dict:
        return {"name": self.name, "api_url": self.api_url, "ca_data": self.ca_data, "token": self.token}


class VaultConfigRow(Base):
    """Singleton row (id=1) holding the runtime Vault integration config —
    same sensitivity as the Secret it replaces (carries the Vault token)."""

    __tablename__ = "vault_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    addr: Mapped[str] = mapped_column(String(500), default="")
    token: Mapped[str] = mapped_column(String, default="")
    mount: Mapped[str] = mapped_column(String(255), default="secret")
    base_path: Mapped[str] = mapped_column(String(500), default="clustervision/users")
    namespace: Mapped[str] = mapped_column(String(255), default="")
    tls_skip_verify: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "addr": self.addr,
            "token": self.token,
            "mount": self.mount,
            "base_path": self.base_path,
            "namespace": self.namespace,
            "tls_skip_verify": self.tls_skip_verify,
        }
