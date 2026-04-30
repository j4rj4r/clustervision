import asyncio
from fastapi import APIRouter, Depends, HTTPException

from ..core.dependencies import require_admin
from ..models.auth import UserInfo
from ..core.async_utils import run_sync
from ..core.kubernetes_client import get_local_api_client
from ..services.drift_service import DriftService

router = APIRouter(prefix="/api/v1/drift", tags=["drift"])

_drift_svc: DriftService | None = None


def get_drift_service() -> DriftService:
    global _drift_svc
    if _drift_svc is None:
        _drift_svc = DriftService(get_local_api_client())
    return _drift_svc


@router.get("/events")
async def list_drift_events(
    limit: int = 50,
    _: UserInfo = Depends(require_admin),
):
    svc = get_drift_service()
    return {
        "events": svc.get_events(limit),
        "total": svc.event_count,
    }


@router.post("/scan", status_code=200)
async def trigger_scan(_: UserInfo = Depends(require_admin)):
    svc = get_drift_service()
    new_events = await run_sync(svc.scan)
    return {"new_events": new_events, "count": len(new_events)}


@router.delete("/events", status_code=204)
async def clear_events(_: UserInfo = Depends(require_admin)):
    get_drift_service().clear()
