import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..core.async_utils import run_sync
from ..core.csv_export import as_utc, rows_to_csv
from ..core.dependencies import require_admin
from ..dependencies import get_audit_service
from ..models.audit import AuditLogPage
from ..models.auth import UserInfo
from ..services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

_EXPORT_COLUMNS = ["timestamp", "actor", "actor_role", "method", "path", "status_code", "payload"]


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


@router.get(
    "/export",
    summary="Export audit log as CSV",
    description=(
        "Unpaginated CSV export for compliance/access-review evidence. "
        "`from`/`to` filter on timestamp; omit both to export everything."
    ),
    responses={200: {"content": {"text/csv": {}}, "description": "CSV file"}},
)
async def export_audit_log(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    actor: str | None = None,
    path_contains: str | None = None,
    _: UserInfo = Depends(require_admin),
    svc: AuditService = Depends(get_audit_service),
):
    rows = await run_sync(svc.export_entries, as_utc(from_), as_utc(to), actor, path_contains)
    for row in rows:
        if row.get("payload") is not None:
            row["payload"] = json.dumps(row["payload"])
    csv_body = rows_to_csv(rows, _EXPORT_COLUMNS)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clustervision-audit-log.csv"'},
    )
