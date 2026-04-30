from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.dependencies import require_admin
from ..models.auth import UserInfo
from ..services.vault_service import configure_vault, get_vault_service, VaultError

router = APIRouter(prefix="/api/v1/admin/vault", tags=["admin"])


class VaultConfig(BaseModel):
    addr: str
    token: str
    mount: str = "secret"
    base_path: str = "clustervision/users"
    namespace: str = ""


@router.get("/status")
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
        "healthy": healthy,
    }


@router.put("/config", status_code=200)
async def set_vault_config(body: VaultConfig, _: UserInfo = Depends(require_admin)):
    try:
        svc = configure_vault(body.model_dump())
        healthy = svc.health_check()
        if not healthy:
            raise HTTPException(status_code=502, detail="Vault configured but health check failed — check addr and token")
        return {"enabled": True, "healthy": True, "addr": svc.addr}
    except VaultError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/config", status_code=204)
async def disable_vault(_: UserInfo = Depends(require_admin)):
    from ..services import vault_service as _mod
    _mod._instance = None
