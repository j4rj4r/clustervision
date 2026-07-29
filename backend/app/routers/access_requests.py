from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..core.async_utils import run_sync
from ..core.csv_export import as_utc, rows_to_csv
from ..core.dependencies import get_current_user, require_admin
from ..dependencies import get_access_request_service
from ..models.access_request import (
    AccessRequestCreate,
    AccessRequestRead,
    JitRolePolicyRead,
    JitRolePolicySet,
)
from ..models.auth import UserInfo
from ..services.access_request_service import (
    AccessRequestError,
    AccessRequestNotFoundError,
    AccessRequestService,
)

router = APIRouter(prefix="/api/v1/access-requests", tags=["access-requests"])

_400 = {400: {"description": "Invalid request or state transition"}}
_404 = {404: {"description": "Access request not found"}}
_EXPORT_COLUMNS = [
    "id", "requester", "target_username", "user_kind", "sa_namespace", "role_name", "role_kind",
    "namespace", "ttl_minutes", "reason", "status", "requested_at", "reviewed_by", "reviewed_at",
    "expires_at", "binding_name",
]


@router.get(
    "",
    response_model=list[AccessRequestRead],
    summary="List access requests",
    description="Admins see every request; other users see only their own.",
)
async def list_access_requests(
    user: UserInfo = Depends(get_current_user),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    requester_filter = None if user.role == "admin" else user.username
    return await run_sync(svc.list_requests, requester_filter)


@router.get(
    "/export",
    summary="Export access requests as CSV",
    description=(
        "Unpaginated CSV export for access-review evidence — every request, "
        "requester, approver, role, and outcome. `from`/`to` filter on request date."
    ),
    responses={200: {"content": {"text/csv": {}}, "description": "CSV file"}},
)
async def export_access_requests(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    _: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    rows = await run_sync(svc.export_requests, as_utc(from_), as_utc(to))
    csv_body = rows_to_csv(rows, _EXPORT_COLUMNS)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clustervision-access-requests.csv"'},
    )


@router.post(
    "",
    response_model=AccessRequestRead,
    status_code=201,
    summary="Request temporary access",
    description=(
        "Any authenticated user can request a time-boxed role grant for a "
        "managed Kubernetes user or ServiceAccount. Nothing is granted until "
        "an admin approves the request."
    ),
    responses={**_400},
)
async def create_access_request(
    payload: AccessRequestCreate,
    user: UserInfo = Depends(get_current_user),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    try:
        return await run_sync(
            svc.create_request,
            user.username,
            payload.target_username,
            payload.user_kind,
            payload.role_name,
            payload.role_kind,
            payload.ttl_minutes,
            payload.reason,
            payload.namespace,
            payload.sa_namespace,
        )
    except AccessRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{request_id}/approve",
    response_model=AccessRequestRead,
    summary="Approve a pending request",
    description="Creates the time-boxed binding. Cannot approve your own request.",
    responses={**_400, **_404},
)
async def approve_access_request(
    request_id: str,
    admin: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    try:
        return await run_sync(svc.approve_request, request_id, admin.username)
    except AccessRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AccessRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{request_id}/deny",
    response_model=AccessRequestRead,
    summary="Deny a pending request",
    responses={**_400, **_404},
)
async def deny_access_request(
    request_id: str,
    admin: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    try:
        return await run_sync(svc.deny_request, request_id, admin.username)
    except AccessRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AccessRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/policies",
    response_model=list[JitRolePolicyRead],
    summary="List JIT role policy overrides",
    description=(
        "Roles with no override are eligible for JIT with the default TTL cap. "
        "An override can mark a role ineligible entirely, or tighten its TTL cap."
    ),
)
async def list_jit_policies(
    _: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    return await run_sync(svc.list_policies)


@router.put(
    "/policies/{role_kind}/{role_name}",
    response_model=JitRolePolicyRead,
    summary="Set a JIT role policy override",
)
async def set_jit_policy(
    role_kind: Literal["ClusterRole", "Role"],
    role_name: str,
    payload: JitRolePolicySet,
    _: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    return await run_sync(svc.set_policy, role_kind, role_name, payload.eligible, payload.max_ttl_minutes)


@router.delete(
    "/policies/{role_kind}/{role_name}",
    status_code=204,
    summary="Remove a JIT role policy override",
    description="Reverts the role to the default: eligible, capped at the global TTL limit.",
)
async def delete_jit_policy(
    role_kind: Literal["ClusterRole", "Role"],
    role_name: str,
    _: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    await run_sync(svc.delete_policy, role_kind, role_name)


@router.post(
    "/{request_id}/revoke",
    response_model=AccessRequestRead,
    summary="Revoke an active grant early",
    description="Deletes the binding immediately instead of waiting for natural expiry.",
    responses={**_400, **_404},
)
async def revoke_access_request(
    request_id: str,
    admin: UserInfo = Depends(require_admin),
    svc: AccessRequestService = Depends(get_access_request_service),
):
    try:
        return await run_sync(svc.revoke_request, request_id, admin.username)
    except AccessRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AccessRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
