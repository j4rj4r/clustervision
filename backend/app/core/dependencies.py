from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..models.auth import UserInfo
from .auth import decode_token

_bearer = HTTPBearer(auto_error=False)

_INSTANCE_SCOPE = "_instance"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserInfo:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials, expected_type="access")
    return UserInfo(username=payload["sub"], roles=payload["roles"])


def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Instance-scope admin — governs login accounts, the cluster registry,
    Vault config, the audit log, and JIT policy config."""
    if user.roles.get(_INSTANCE_SCOPE) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_approver(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Instance-scope admin or approver — can approve/deny JIT access requests."""
    if user.roles.get(_INSTANCE_SCOPE) not in ("admin", "approver"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approver access required")
    return user


def instance_gate(request: Request, user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Instance-scope equivalent of auth_gate: GET/HEAD open to any
    authenticated user (the cluster registry listing is non-sensitive picker
    metadata), mutations require instance admin."""
    if request.method not in ("GET", "HEAD", "OPTIONS") and user.roles.get(_INSTANCE_SCOPE) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def auth_gate(
    request: Request,
    cluster: str = Query("local"),
    user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    """Cluster-scoped gate: no role at all on the target `?cluster=` means no
    access, including GET — operator or admin is required for mutations."""
    role = user.roles.get(cluster)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to cluster '{cluster}'")
    if request.method not in ("GET", "HEAD", "OPTIONS") and role not in ("operator", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator access required")
    return user
