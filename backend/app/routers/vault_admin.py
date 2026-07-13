from functools import partial

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.async_utils import run_sync
from ..core.dependencies import require_admin
from ..models.auth import UserInfo
from ..services.vault_service import (
    get_vault_service, configure_vault, disable_vault,
)

router = APIRouter(prefix="/api/v1/admin/vault", tags=["admin"])


class VaultConfig(BaseModel):
    addr: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)
    mount: str = "secret"
    base_path: str = "clustervision/users"
    namespace: str = ""
    tls_skip_verify: bool = False


def _status_payload(svc) -> dict:
    return {
        "enabled": True,
        "addr": svc.addr,
        "mount": svc.mount,
        "base_path": svc.base_path,
        "namespace": svc.namespace,
        "tls_skip_verify": svc.tls_skip_verify,
        "healthy": svc._cached_healthy,
        "error": svc._cached_error,
    }


@router.get("/status", summary="Vault integration status")
async def vault_status(_: UserInfo = Depends(require_admin)):
    # get_vault_service may re-sync from the config Secret — off the event loop
    svc = await run_sync(get_vault_service)
    if not svc:
        return {"enabled": False}
    # Live check so the admin panel shows the current state, not the one
    # cached at configure time
    await run_sync(svc.health_check)
    return _status_payload(svc)


@router.put("/config", summary="Configure Vault integration")
async def set_vault_config(payload: VaultConfig, _: UserInfo = Depends(require_admin)):
    # Persists the config to a K8s Secret (shared across workers/restarts)
    svc = await run_sync(partial(
        configure_vault,
        addr=payload.addr,
        token=payload.token,
        mount=payload.mount,
        base_path=payload.base_path,
        namespace=payload.namespace,
        tls_skip_verify=payload.tls_skip_verify,
    ))
    await run_sync(svc.health_check)
    return _status_payload(svc)


@router.delete("/config", status_code=204, summary="Disable Vault integration")
async def delete_vault_config(_: UserInfo = Depends(require_admin)):
    await run_sync(disable_vault)
