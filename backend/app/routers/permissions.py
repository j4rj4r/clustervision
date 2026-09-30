from fastapi import APIRouter, Depends

from ..core.dependencies import require_admin
from ..models.auth import UserInfo
from ..models.permissions import ScopeRoleRead, ScopeRoleSet
from ..services.auth_service import (
    delete_scope_role,
    list_scope_roles,
    list_scopes,
    set_scope_role,
)

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


@router.get("/scopes", response_model=list[str], summary="List assignable scopes")
async def get_scopes(_: UserInfo = Depends(require_admin)):
    return list_scopes()


@router.get(
    "/users/{username}",
    response_model=list[ScopeRoleRead],
    summary="List a user's scope roles",
)
async def get_user_roles(username: str, _: UserInfo = Depends(require_admin)):
    return list_scope_roles(username)


@router.put(
    "/users/{username}/{scope}",
    response_model=ScopeRoleRead,
    summary="Set a user's role on a scope",
)
async def put_user_role(
    username: str, scope: str, body: ScopeRoleSet, _: UserInfo = Depends(require_admin)
):
    set_scope_role(username, scope, body.role)
    return ScopeRoleRead(scope=scope, role=body.role)


@router.delete(
    "/users/{username}/{scope}",
    status_code=204,
    summary="Remove a user's role on a scope",
)
async def delete_user_role(
    username: str, scope: str, _: UserInfo = Depends(require_admin)
):
    delete_scope_role(username, scope)
