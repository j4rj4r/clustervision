import os
import time
from collections import defaultdict
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..core.async_utils import run_sync
from ..core.auth import create_access_token, create_refresh_token, decode_token
from ..core.dependencies import get_current_user, require_admin
from ..models.auth import LoginRequest, TokenResponse, UserInfo
from ..services.auth_service import (
    authenticate,
    change_password,
    change_role,
    create_user,
    delete_user,
    get_user_entry,
    list_users,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Login rate limiting ────────────────────────────────────────────────────
_RATE_LIMIT = 10        # max attempts
_RATE_WINDOW = 300      # per 5 minutes
_rate_lock = Lock()
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    # Behind the ingress, request.client.host is the proxy IP — without this,
    # every user shares a single rate-limit bucket.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        if len(_rate_buckets) > 1024:
            stale = [k for k, v in _rate_buckets.items() if not v or now - v[-1] >= _RATE_WINDOW]
            for k in stale:
                del _rate_buckets[k]
        attempts = [t for t in _rate_buckets[ip] if now - t < _RATE_WINDOW]
        if len(attempts) >= _RATE_LIMIT:
            _rate_buckets[ip] = attempts
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts — try again later",
                headers={"Retry-After": str(_RATE_WINDOW)},
            )
        attempts.append(now)
        _rate_buckets[ip] = attempts

_REFRESH_COOKIE = "cv_refresh"
_REFRESH_MAX_AGE = 7 * 86400
_SECURE_COOKIE = os.environ.get("CV_SECURE_COOKIE", "true").lower() != "false"
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="strict",
        max_age=_REFRESH_MAX_AGE,
        path=_COOKIE_PATH,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response):
    _check_rate_limit(_client_ip(request))
    # bcrypt + K8s secret read are blocking — keep them off the event loop
    user = await run_sync(authenticate, body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(user["username"], user["role"])
    refresh_token = create_refresh_token(user["username"], user["role"])
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        role=user["role"],
        username=user["username"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(cv_refresh: Annotated[str | None, Cookie()] = None):
    if not cv_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(cv_refresh, expected_type="refresh")
    # Re-check the user store: a deleted user must not outlive their refresh
    # token, and a role change must apply immediately.
    user = await run_sync(get_user_entry, payload["sub"])
    if not user:
        resp = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "User no longer exists"},
        )
        resp.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)
        return resp
    access_token = create_access_token(user["username"], user["role"])
    return TokenResponse(
        access_token=access_token,
        role=user["role"],
        username=user["username"],
    )


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user


# ── Admin: manage CV users ─────────────────────────────────────────────────

class CreateUserBody(LoginRequest):
    role: str = "viewer"


@router.get("/users", response_model=list[dict])
async def get_users(_: UserInfo = Depends(require_admin)):
    return list_users()


@router.post("/users", status_code=201)
async def add_user(body: CreateUserBody, _: UserInfo = Depends(require_admin)):
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'viewer'")
    create_user(body.username, body.password, body.role)
    return {"username": body.username, "role": body.role}


@router.delete("/users/{username}", status_code=204)
async def remove_user(username: str, current: UserInfo = Depends(require_admin)):
    if username == current.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    delete_user(username)


class ChangeRoleBody(BaseModel):
    role: str


@router.patch("/users/{username}/role", status_code=204)
async def update_role(username: str, body: ChangeRoleBody, current: UserInfo = Depends(require_admin)):
    if body.role not in ("admin", "viewer"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'viewer'")
    if username == current.username:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    change_role(username, body.role)


@router.post("/users/{username}/password", status_code=204)
async def reset_password(
    username: str,
    body: LoginRequest,
    _: UserInfo = Depends(require_admin),
):
    change_password(username, body.password)
