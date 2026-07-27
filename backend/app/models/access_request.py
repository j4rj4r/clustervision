from typing import Literal

from pydantic import BaseModel, Field

MIN_TTL_MINUTES = 5
MAX_TTL_MINUTES = 24 * 60


class AccessRequestCreate(BaseModel):
    # The K8s-managed identity that would receive the grant — independent from
    # the ClusterVision login account making the request (the two are
    # unrelated registries; a viewer can request temporary access on behalf of
    # any managed user or ServiceAccount, an admin decides whether to grant it)
    target_username: str = Field(..., min_length=1, max_length=253)
    user_kind: Literal["User", "ServiceAccount"] = "User"
    sa_namespace: str | None = Field(None, max_length=63)
    role_name: str = Field(..., min_length=1)
    role_kind: Literal["ClusterRole", "Role"] = "ClusterRole"
    namespace: str | None = Field(None, max_length=63)
    ttl_minutes: int = Field(..., ge=MIN_TTL_MINUTES, le=MAX_TTL_MINUTES)
    reason: str = Field(..., min_length=1, max_length=500)


class AccessRequestRead(BaseModel):
    id: str
    requester: str
    target_username: str
    user_kind: str
    sa_namespace: str | None = None
    role_name: str
    role_kind: str
    namespace: str | None = None
    ttl_minutes: int
    reason: str
    status: Literal["pending", "approved", "denied", "revoked", "expired"]
    requested_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    expires_at: str | None = None
    binding_name: str | None = None
