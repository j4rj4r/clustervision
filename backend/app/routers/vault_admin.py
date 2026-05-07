from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..core.dependencies import require_admin
from ..models.auth import UserInfo
from ..services.vault_service import (
    get_vault_service, configure_vault, disable_vault, VaultError,
)

router = APIRouter(prefix="/api/v1/admin/vault", tags=["admin"])


class VaultConfig(BaseModel):
    addr: str
    token: str
    mount: str = "secret"
    base_path: str = "clustervision/users"
    namespace: str = ""


@router.get("/status", summary="Vault integration status")
async def vault_status(_: UserInfo = Depends(require_admin)):
    svc = get_vault_service()
    if not svc:
        return {"enabled": False}
    healthy = svc.health_check()
    return {
        "enabled": True,
        "addr": svc.addr,
        "mount": svc.mount,
        "base_path": svc.base_path,
        "namespace": svc.namespace,
        "healthy": healthy,
    }


@router.put("/config", summary="Configure Vault integration")
async def set_vault_config(payload: VaultConfig, _: UserInfo = Depends(require_admin)):
    svc = configure_vault(
        addr=payload.addr,
        token=payload.token,
        mount=payload.mount,
        base_path=payload.base_path,
        namespace=payload.namespace,
    )
    try:
        healthy = svc.health_check()
    except VaultError:
        healthy = False
    return {"enabled": True, "healthy": healthy, "addr": svc.addr}


@router.delete("/config", status_code=204, summary="Disable Vault integration")
async def delete_vault_config(_: UserInfo = Depends(require_admin)):
    disable_vault()
