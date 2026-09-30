import os
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from ..core.async_utils import run_sync
from ..core.auth import create_access_token, create_refresh_token, decode_token
from ..core.dependencies import get_current_user, require_admin
from ..models.auth import (
    LinkedUserRead,
    LinkedUserSet,
    LoginRequest,
    TokenResponse,
    UserInfo,
)
from ..services.auth_service import (
    authenticate,
    change_password,
    check_login_rate_limit,
    clear_linked_user,
    create_user,
    delete_user,
    get_linked_user,
    get_user_entry,
    list_users,
    set_linked_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    # Behind the ingress, request.client.host is the proxy IP — without this,
    # every user shares a single rate-limit bucket.
    #
    # Take the LAST hop, not the first: Traefik (and most reverse proxies)
    # append the real client IP to any X-Forwarded-For already present on the
    # inbound request rather than replacing it, so the first entry is
    # attacker-controlled — trusting it lets anyone reset their own bucket by
    # sending a different X-Forwarded-For on every attempt.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


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
    await run_sync(check_login_rate_limit, _client_ip(request))
    # bcrypt + K8s secret read are blocking — keep them off the event loop
    user = await run_sync(authenticate, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    access_token = create_access_token(user["username"], user["roles"])
    refresh_token = create_refresh_token(user["username"], user["roles"])
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        roles=user["roles"],
        username=user["username"],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(cv_refresh: Annotated[str | None, Cookie()] = None):
    if not cv_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )
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
    access_token = create_access_token(user["username"], user["roles"])
    return TokenResponse(
        access_token=access_token,
        roles=user["roles"],
        username=user["username"],
    )


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)


@router.get("/me", response_model=UserInfo)
async def me(user: UserInfo = Depends(get_current_user)):
    return user


@router.get("/me/link", response_model=LinkedUserRead | None)
async def my_link(user: UserInfo = Depends(get_current_user)):
    return get_linked_user(user.username)


# ── Admin: manage CV users ─────────────────────────────────────────────────
# Accounts are created with just username/password — scope role assignments
# are managed separately via /api/v1/permissions (see routers/permissions.py).


class CreateUserBody(LoginRequest):
    pass


@router.get("/users", response_model=list[dict])
async def get_users(_: UserInfo = Depends(require_admin)):
    return list_users()


@router.post("/users", status_code=201)
async def add_user(body: CreateUserBody, _: UserInfo = Depends(require_admin)):
    create_user(body.username, body.password)
    return {"username": body.username}


@router.delete("/users/{username}", status_code=204)
async def remove_user(username: str, current: UserInfo = Depends(require_admin)):
    if username == current.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    delete_user(username)


@router.post("/users/{username}/password", status_code=204)
async def reset_password(
    username: str,
    body: LoginRequest,
    _: UserInfo = Depends(require_admin),
):
    change_password(username, body.password)


@router.put("/users/{username}/link", response_model=LinkedUserRead)
async def link_user(
    username: str, body: LinkedUserSet, _: UserInfo = Depends(require_admin)
):
    set_linked_user(username, body.name, body.namespace)
    return LinkedUserRead(name=body.name, namespace=body.namespace)


@router.delete("/users/{username}/link", status_code=204)
async def unlink_user(username: str, _: UserInfo = Depends(require_admin)):
    clear_linked_user(username)
