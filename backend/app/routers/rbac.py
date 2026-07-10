from fastapi import APIRouter, Depends, Query

from ..models.rbac import (
    ClusterRoleCreate, RoleCreate, RoleUpdate, BindingCreate,
    AssignRoleRequest, RoleRead, BindingRead, UserPermissionSummary,
    NamespaceAccessEntry, CheckAccessRequest, CheckAccessResult, PaginatedList,
)
from ..services.rbac_service import RbacService
from ..services.certificate_service import CertificateService
from ..services.service_account_service import ServiceAccountService
from ..dependencies import get_rbac_service, get_cert_service, get_sa_service
from typing import Optional
from ..core.async_utils import run_sync
from ..core.exceptions import UserNotFoundError

router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])

_404 = {404: {"description": "Resource not found"}}
_403 = {403: {"description": "Insufficient Kubernetes permissions"}}


# ── ClusterRoles ─────────────────────────────────────────────────────────────

@router.get(
    "/cluster-roles",
    response_model=PaginatedList[RoleRead],
    summary="List ClusterRoles",
    description=(
        "Returns ClusterRoles up to `limit`. Set `include_system=true` to include Kubernetes built-in roles. "
        "Use `continue` (from a previous response's `next_continue`) to fetch the next page."
    ),
)
async def list_cluster_roles(
    include_system: bool = False,
    limit: int = Query(default=500, ge=1, le=1000),
    cursor: Optional[str] = Query(default=None, alias="continue"),
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.list_cluster_roles, include_system, limit, cursor)


@router.post(
    "/cluster-roles",
    response_model=RoleRead,
    status_code=201,
    summary="Create a ClusterRole",
    description="Create a new ClusterRole with the given policy rules.",
    responses={**_403},
)
async def create_cluster_role(
    payload: ClusterRoleCreate,
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.create_cluster_role, payload.name, payload.rules)


@router.patch(
    "/cluster-roles/{name}",
    response_model=RoleRead,
    summary="Update a ClusterRole",
    description="Replace the policy rules of an existing ClusterRole.",
    responses={**_404, **_403},
)
async def update_cluster_role(
    name: str,
    payload: RoleUpdate,
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.update_cluster_role, name, payload.rules)


@router.delete(
    "/cluster-roles/{name}",
    status_code=204,
    summary="Delete a ClusterRole",
    description="Delete a ClusterRole by name. System roles cannot be deleted via this API.",
    responses={**_404, **_403},
)
async def delete_cluster_role(name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_cluster_role, name)


# ── Namespaced Roles ──────────────────────────────────────────────────────────

@router.get(
    "/roles/{namespace}",
    response_model=PaginatedList[RoleRead],
    summary="List Roles in a namespace",
    description="Returns Roles in the given namespace up to `limit`. Use `continue` for the next page.",
)
async def list_roles(
    namespace: str,
    limit: int = Query(default=500, ge=1, le=1000),
    cursor: Optional[str] = Query(default=None, alias="continue"),
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.list_roles, namespace, limit, cursor)


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=201,
    summary="Create a Role",
    description="Create a new namespaced Role.",
    responses={**_403},
)
async def create_role(payload: RoleCreate, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.create_role, payload.namespace, payload.name, payload.rules)


@router.patch(
    "/roles/{namespace}/{name}",
    response_model=RoleRead,
    summary="Update a Role",
    description="Replace the policy rules of an existing namespaced Role.",
    responses={**_404, **_403},
)
async def update_role(
    namespace: str,
    name: str,
    payload: RoleUpdate,
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.update_role, namespace, name, payload.rules)


@router.delete(
    "/roles/{namespace}/{name}",
    status_code=204,
    summary="Delete a Role",
    description="Delete a namespaced Role.",
    responses={**_404, **_403},
)
async def delete_role(namespace: str, name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_role, namespace, name)


# ── ClusterRoleBindings ───────────────────────────────────────────────────────

@router.get(
    "/bindings/cluster",
    response_model=PaginatedList[BindingRead],
    summary="List ClusterRoleBindings",
    description="Returns ClusterRoleBindings up to `limit`. Use `continue` for the next page.",
)
async def list_cluster_bindings(
    limit: int = Query(default=500, ge=1, le=1000),
    cursor: Optional[str] = Query(default=None, alias="continue"),
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.list_cluster_role_bindings, limit, cursor)


@router.post(
    "/bindings/cluster",
    response_model=BindingRead,
    status_code=201,
    summary="Create a ClusterRoleBinding",
    responses={**_403},
)
async def create_cluster_binding(payload: BindingCreate, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.create_cluster_role_binding, payload.name, payload.role_name, payload.subjects)


@router.delete(
    "/bindings/cluster/{name}",
    status_code=204,
    summary="Delete a ClusterRoleBinding",
    responses={**_404, **_403},
)
async def delete_cluster_binding(name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_cluster_role_binding, name)


# ── RoleBindings ──────────────────────────────────────────────────────────────

@router.get(
    "/bindings/namespace/{namespace}",
    response_model=list[BindingRead],
    summary="List RoleBindings in a namespace",
)
async def list_namespace_bindings(namespace: str, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_role_bindings, namespace)


@router.post(
    "/bindings/namespace/{namespace}",
    response_model=BindingRead,
    status_code=201,
    summary="Create a RoleBinding",
    responses={**_403},
)
async def create_namespace_binding(
    namespace: str, payload: BindingCreate, svc: RbacService = Depends(get_rbac_service)
):
    return await run_sync(
        svc.create_role_binding,
        namespace,
        payload.name,
        payload.role_name,
        payload.role_kind,
        payload.subjects,
    )


@router.delete(
    "/bindings/namespace/{namespace}/{name}",
    status_code=204,
    summary="Delete a RoleBinding",
    responses={**_404, **_403},
)
async def delete_namespace_binding(
    namespace: str, name: str, svc: RbacService = Depends(get_rbac_service)
):
    await run_sync(svc.delete_role_binding, namespace, name)


# ── User-centric endpoints ────────────────────────────────────────────────────

@router.get(
    "/users/{username}/permissions",
    response_model=UserPermissionSummary,
    summary="Get user permissions",
    description=(
        "Returns all ClusterRoleBindings and RoleBindings that reference this user. "
        "Makes two Kubernetes API calls (one for CRBs, one for all RoleBindings)."
    ),
    responses={**_404},
)
async def get_user_permissions(username: str, svc: RbacService = Depends(get_rbac_service)):
    import asyncio
    cluster_bindings, namespace_bindings = await asyncio.gather(
        run_sync(svc._cluster_bindings_for, username),
        run_sync(svc._namespace_bindings_for, username),
    )
    return {
        "username": username,
        "cluster_bindings": cluster_bindings,
        "namespace_bindings": namespace_bindings,
    }


@router.post(
    "/users/{username}/roles",
    status_code=204,
    summary="Assign a role to a user",
    description=(
        "Create or update a binding to grant `role_name` to `username`. "
        "If `namespace` is omitted and `role_kind` is `ClusterRole`, a ClusterRoleBinding is created. "
        "Otherwise a namespaced RoleBinding is created. "
        "For ServiceAccount subjects, supply `sa_namespace` (the SA's namespace)."
    ),
    responses={**_403},
)
async def assign_role(
    username: str,
    payload: AssignRoleRequest,
    user_kind: str = "User",
    sa_namespace: str = None,
    svc: RbacService = Depends(get_rbac_service),
):
    await run_sync(
        svc.assign_role,
        username,
        user_kind,
        payload.role_name,
        payload.role_kind,
        payload.namespace,
        sa_namespace,
    )


@router.delete(
    "/users/{username}/roles/{role_name}",
    status_code=204,
    summary="Revoke a role from a user",
    description=(
        "Delete the binding `clustervision-{username}-{role_name}`. "
        "If `namespace` is omitted, looks for a ClusterRoleBinding; otherwise a namespaced RoleBinding."
    ),
    responses={**_404},
)
async def revoke_role(
    username: str,
    role_name: str,
    namespace: str = None,
    svc: RbacService = Depends(get_rbac_service),
):
    await run_sync(svc.revoke_role, username, role_name, namespace)


# ── Namespaces ────────────────────────────────────────────────────────────────

@router.get(
    "/namespaces",
    response_model=list[str],
    summary="List namespaces",
    description="Returns the names of all namespaces in the cluster.",
)
async def list_namespaces(svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_namespaces)


# ── Namespace access view ─────────────────────────────────────────────────────

@router.get(
    "/namespace/{namespace}/access",
    response_model=list[NamespaceAccessEntry],
    summary="Who has access to a namespace",
    description=(
        "Returns all subjects (users, groups, service accounts) that have access to the namespace, "
        "from both namespaced RoleBindings and cluster-wide ClusterRoleBindings."
    ),
)
async def get_namespace_access(namespace: str, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.get_namespace_access, namespace)


# ── Access simulator ──────────────────────────────────────────────────────────

@router.post(
    "/check-access",
    response_model=CheckAccessResult,
    summary="Check if a user can perform an action",
    description=(
        "Uses the Kubernetes SubjectAccessReview API to test whether `user` can perform `verb` "
        "on `resource` (optionally scoped to a `namespace` and `api_group`). "
        "Equivalent to `kubectl auth can-i <verb> <resource> --as <user>`. "
        "Registry users are resolved to their real authentication subject: ServiceAccounts become "
        "`system:serviceaccount:<ns>:<name>` with their implicit groups, certificate users carry "
        "their O= groups. Unknown names are simulated as-is."
    ),
)
async def check_access(
    payload: CheckAccessRequest,
    svc: RbacService = Depends(get_rbac_service),
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    # Resolve the registry user to the subject the API server actually sees at
    # authentication time — otherwise SA users and group-derived permissions
    # simulate as denied even though real access works.
    sar_user = payload.user
    groups: list[str] = []
    try:
        cert_user = await run_sync(cert_svc.get_user, payload.user)
        groups = list(cert_user.get("groups") or []) + ["system:authenticated"]
    except UserNotFoundError:
        try:
            sa_user = await run_sync(sa_svc.get_user, payload.user)
            sa_ns = sa_user.get("namespace", "default")
            sar_user = f"system:serviceaccount:{sa_ns}:{payload.user}"
            groups = [
                "system:serviceaccounts",
                f"system:serviceaccounts:{sa_ns}",
                "system:authenticated",
            ]
        except UserNotFoundError:
            pass  # not a registry user — simulate the raw name unchanged

    return await run_sync(
        svc.check_access,
        sar_user,
        payload.verb,
        payload.resource,
        payload.namespace,
        payload.api_group,
        groups,
    )
