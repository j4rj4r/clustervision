from fastapi import APIRouter, Depends, Query

from ..core.async_utils import run_sync
from ..core.dependencies import require_admin
from ..dependencies import get_audit_service
from ..models.audit import AuditLogPage
from ..models.auth import UserInfo
from ..services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get(
    "",
    response_model=AuditLogPage,
    summary="List audit log entries",
    description=(
        "Every mutating request against RBAC, users, tokens, cluster-registry and Vault-config "
        "endpoints — who, what, and whether it succeeded. Ordered newest first."
    ),
)
async def list_audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: str | None = None,
    path_contains: str | None = None,
    _: UserInfo = Depends(require_admin),
    svc: AuditService = Depends(get_audit_service),
):
    items, total = await run_sync(svc.list_entries, limit, offset, actor, path_contains)
    return {"items": items, "total": total}
