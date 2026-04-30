from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.dependencies import get_current_user, require_admin
from ..models.auth import UserInfo
from ..core.async_utils import run_sync
from ..services import access_request_service as svc
from ..services.rbac_service import RbacService
from ..dependencies import get_rbac_service

router = APIRouter(prefix="/api/v1/access-requests", tags=["access-requests"])


class CreateRequestBody(BaseModel):
    role_name: str
    role_kind: str = "ClusterRole"
    namespace: str | None = None
    justification: str


class DenyBody(BaseModel):
    reason: str = ""


@router.get("")
async def list_requests(
    status: str | None = None,
    user: UserInfo = Depends(get_current_user),
):
    # Admins see all; viewers see only their own
    username_filter = None if user.role == "admin" else user.username
    return await run_sync(svc.list_requests, username_filter, status)


@router.post("", status_code=201)
async def create_request(
    body: CreateRequestBody,
    user: UserInfo = Depends(get_current_user),
):
    return await run_sync(
        svc.create_request,
        user.username,
        body.role_name,
        body.role_kind,
        body.namespace,
        body.justification,
    )


@router.post("/{request_id}/approve", status_code=200)
async def approve_request(
    request_id: str,
    admin: UserInfo = Depends(require_admin),
    rbac_svc: RbacService = Depends(get_rbac_service),
):
    try:
        req = await run_sync(svc.resolve_request, request_id, admin.username, True)
    except KeyError:
        raise HTTPException(status_code=404, detail="Request not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Auto-apply the binding
    await run_sync(
        rbac_svc.assign_role,
        req["requester"],
        "User",
        req["role_name"],
        req["role_kind"],
        req["namespace"],
        None,
    )
    return req


@router.post("/{request_id}/deny", status_code=200)
async def deny_request(
    request_id: str,
    body: DenyBody,
    admin: UserInfo = Depends(require_admin),
):
    try:
        return await run_sync(svc.resolve_request, request_id, admin.username, False, body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Request not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{request_id}", status_code=204)
async def cancel_request(
    request_id: str,
    user: UserInfo = Depends(get_current_user),
):
    try:
        await run_sync(svc.cancel_request, request_id, user.username)
    except KeyError:
        raise HTTPException(status_code=404, detail="Request not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
