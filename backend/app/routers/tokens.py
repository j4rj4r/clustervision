from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..services.token_service import TokenService
from ..dependencies import get_token_service
from ..core.async_utils import run_sync

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("/history")
async def list_history(svc: TokenService = Depends(get_token_service)):
    return await run_sync(svc.list_history)


@router.delete("/history", status_code=204)
async def clear_history(svc: TokenService = Depends(get_token_service)):
    await run_sync(svc.clear_history)


@router.delete("/history/{entry_id}", status_code=204)
async def delete_history_entry(entry_id: str, svc: TokenService = Depends(get_token_service)):
    await run_sync(svc.delete_history_entry, entry_id)


@router.get("/sa-tokens")
async def list_sa_tokens(svc: TokenService = Depends(get_token_service)):
    return await run_sync(svc.list_sa_tokens)


@router.delete("/sa-tokens/{secret_name}", status_code=204)
async def revoke_sa_token(
    secret_name: str,
    namespace: str,
    svc: TokenService = Depends(get_token_service),
):
    await run_sync(svc.revoke_sa_token, secret_name, namespace)


class RotateRequest(BaseModel):
    sa_name: str
    namespace: str


@router.post("/sa-tokens/{secret_name}/rotate", status_code=204)
async def rotate_sa_token(
    secret_name: str,
    payload: RotateRequest,
    svc: TokenService = Depends(get_token_service),
):
    await run_sync(svc.rotate_sa_token, secret_name, payload.sa_name, payload.namespace)
