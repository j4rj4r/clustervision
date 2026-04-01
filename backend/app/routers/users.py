import asyncio
from fastapi import APIRouter, Depends, HTTPException

from ..models.user import UserCreate, UserImport, UserRead, UserWithCredentials, UserList, UserType
from ..services.certificate_service import CertificateService
from ..services.service_account_service import ServiceAccountService
from ..services.rbac_service import RbacService
from ..dependencies import get_cert_service, get_sa_service, get_rbac_service
from ..core.async_utils import run_sync
from ..core.exceptions import UserNotFoundError

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserList)
async def list_users(
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    cert_users, sa_users = await asyncio.gather(
        run_sync(cert_svc.list_users),
        run_sync(sa_svc.list_users),
    )
    all_users = cert_users + sa_users
    return {"users": all_users, "total": len(all_users)}


@router.post("", response_model=UserWithCredentials, status_code=201)
async def create_user(
    payload: UserCreate,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    if payload.user_type == UserType.certificate:
        return await run_sync(cert_svc.create_user, payload.name, payload.groups)
    return await run_sync(sa_svc.create_user, payload.name, payload.namespace)


@router.get("/unmanaged-serviceaccounts")
async def list_unmanaged_service_accounts(
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    return await run_sync(sa_svc.list_unmanaged)


@router.post("/import", response_model=UserRead, status_code=201)
async def import_user(
    payload: UserImport,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    if payload.user_type == UserType.certificate:
        return await run_sync(cert_svc.import_user, payload.name, payload.groups)
    return await run_sync(sa_svc.import_user, payload.name, payload.namespace)


@router.get("/{username}", response_model=UserRead)
async def get_user(
    username: str,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    try:
        return await run_sync(cert_svc.get_user, username)
    except UserNotFoundError:
        pass
    try:
        return await run_sync(sa_svc.get_user, username)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")


@router.delete("/{username}", status_code=204)
async def delete_user(
    username: str,
    user_type: UserType = UserType.certificate,
    namespace: str = "default",
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
    rbac_svc: RbacService = Depends(get_rbac_service),
):
    if user_type == UserType.certificate:
        await run_sync(cert_svc.delete_user, username)
    else:
        await run_sync(sa_svc.delete_user, username, namespace)
    await run_sync(rbac_svc.delete_user_bindings, username)
