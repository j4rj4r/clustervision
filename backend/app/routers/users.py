import asyncio
from fastapi import APIRouter, Depends, HTTPException

from ..models.user import UserCreate, UserImport, UserRead, UserWithCredentials, UserList, UserType
from ..services.certificate_service import CertificateService
from ..services.service_account_service import ServiceAccountService
from ..dependencies import get_cert_service, get_sa_service

router = APIRouter(prefix="/api/users", tags=["users"])


def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, fn, *args)


@router.get("", response_model=UserList)
async def list_users(
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    cert_users, sa_users = await asyncio.gather(
        asyncio.get_event_loop().run_in_executor(None, cert_svc.list_users),
        asyncio.get_event_loop().run_in_executor(None, sa_svc.list_users),
    )
    all_users = cert_users + sa_users
    return {"users": all_users, "total": len(all_users)}


@router.post("", response_model=UserWithCredentials, status_code=201)
async def create_user(
    payload: UserCreate,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    loop = asyncio.get_event_loop()
    if payload.user_type == UserType.certificate:
        result = await loop.run_in_executor(
            None, cert_svc.create_user, payload.name, payload.groups
        )
    else:
        result = await loop.run_in_executor(
            None, sa_svc.create_user, payload.name, payload.namespace
        )
    return result


@router.get("/unmanaged-serviceaccounts")
async def list_unmanaged_service_accounts(
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sa_svc.list_unmanaged)


@router.post("/import", response_model=UserRead, status_code=201)
async def import_user(
    payload: UserImport,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    loop = asyncio.get_event_loop()
    if payload.user_type == UserType.certificate:
        return await loop.run_in_executor(
            None, cert_svc.import_user, payload.name, payload.groups
        )
    else:
        return await loop.run_in_executor(
            None, sa_svc.import_user, payload.name, payload.namespace
        )


@router.get("/{username}", response_model=UserRead)
async def get_user(
    username: str,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    loop = asyncio.get_event_loop()
    # Try cert user first, then SA
    try:
        return await loop.run_in_executor(None, cert_svc.get_user, username)
    except Exception:
        pass
    try:
        return await loop.run_in_executor(None, sa_svc.get_user, username, "default")
    except Exception:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")


@router.delete("/{username}", status_code=204)
async def delete_user(
    username: str,
    user_type: UserType = UserType.certificate,
    namespace: str = "default",
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
):
    loop = asyncio.get_event_loop()
    if user_type == UserType.certificate:
        await loop.run_in_executor(None, cert_svc.delete_user, username)
    else:
        await loop.run_in_executor(None, sa_svc.delete_user, username, namespace)
