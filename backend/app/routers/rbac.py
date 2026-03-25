from fastapi import APIRouter, Depends

from ..models.rbac import (
    ClusterRoleCreate, RoleCreate, BindingCreate,
    AssignRoleRequest, UserPermissionSummary, PolicyRule,
)
from ..services.rbac_service import RbacService
from ..dependencies import get_rbac_service
from ..core.async_utils import run_sync

router = APIRouter(prefix="/api/rbac", tags=["rbac"])


# ── ClusterRoles ─────────────────────────────────────────────────────────────

@router.get("/cluster-roles")
async def list_cluster_roles(
    include_system: bool = False,
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.list_cluster_roles, include_system)


@router.post("/cluster-roles", status_code=201)
async def create_cluster_role(
    payload: ClusterRoleCreate,
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.create_cluster_role, payload.name, payload.rules)


@router.put("/cluster-roles/{name}")
async def update_cluster_role(
    name: str,
    rules: list[PolicyRule],
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.update_cluster_role, name, rules)


@router.delete("/cluster-roles/{name}", status_code=204)
async def delete_cluster_role(name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_cluster_role, name)


# ── Namespaced Roles ──────────────────────────────────────────────────────────

@router.get("/roles/{namespace}")
async def list_roles(namespace: str, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_roles, namespace)


@router.post("/roles", status_code=201)
async def create_role(payload: RoleCreate, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.create_role, payload.namespace, payload.name, payload.rules)


@router.put("/roles/{namespace}/{name}")
async def update_role(
    namespace: str,
    name: str,
    rules: list[PolicyRule],
    svc: RbacService = Depends(get_rbac_service),
):
    return await run_sync(svc.update_role, namespace, name, rules)


@router.delete("/roles/{namespace}/{name}", status_code=204)
async def delete_role(namespace: str, name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_role, namespace, name)


# ── ClusterRoleBindings ───────────────────────────────────────────────────────

@router.get("/bindings/cluster")
async def list_cluster_bindings(svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_cluster_role_bindings)


@router.post("/bindings/cluster", status_code=201)
async def create_cluster_binding(payload: BindingCreate, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.create_cluster_role_binding, payload.name, payload.role_name, payload.subjects)


@router.delete("/bindings/cluster/{name}", status_code=204)
async def delete_cluster_binding(name: str, svc: RbacService = Depends(get_rbac_service)):
    await run_sync(svc.delete_cluster_role_binding, name)


# ── RoleBindings ──────────────────────────────────────────────────────────────

@router.get("/bindings/namespace/{namespace}")
async def list_namespace_bindings(namespace: str, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_role_bindings, namespace)


@router.post("/bindings/namespace/{namespace}", status_code=201)
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


@router.delete("/bindings/namespace/{namespace}/{name}", status_code=204)
async def delete_namespace_binding(
    namespace: str, name: str, svc: RbacService = Depends(get_rbac_service)
):
    await run_sync(svc.delete_role_binding, namespace, name)


# ── User-centric endpoints ────────────────────────────────────────────────────

@router.get("/users/{username}/permissions")
async def get_user_permissions(username: str, svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.get_user_permissions, username)


@router.post("/users/{username}/assign", status_code=204)
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


@router.delete("/users/{username}/revoke", status_code=204)
async def revoke_role(
    username: str,
    role_name: str,
    namespace: str = None,
    svc: RbacService = Depends(get_rbac_service),
):
    await run_sync(svc.revoke_role, username, role_name, namespace)


# ── Namespaces ────────────────────────────────────────────────────────────────

@router.get("/namespaces")
async def list_namespaces(svc: RbacService = Depends(get_rbac_service)):
    return await run_sync(svc.list_namespaces)
