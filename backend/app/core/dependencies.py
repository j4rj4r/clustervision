from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..models.auth import UserInfo
from .auth import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserInfo:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials, expected_type="access")
    return UserInfo(username=payload["sub"], role=payload["role"])


def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def auth_gate(request: Request, user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Allows viewers on GET/HEAD, requires admin for all mutations."""
    if request.method not in ("GET", "HEAD", "OPTIONS") and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
