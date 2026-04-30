import asyncio
from fastapi import APIRouter, Depends

from ..models.auth import UserInfo
from ..core.dependencies import get_current_user
from ..services.rbac_service import RbacService
from ..services.certificate_service import CertificateService
from ..dependencies import get_rbac_service, get_cert_service
from ..core.async_utils import run_sync
from ..core.exceptions import UserNotFoundError

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("/me")
async def get_my_profile(
    user: UserInfo = Depends(get_current_user),
    rbac_svc: RbacService = Depends(get_rbac_service),
    cert_svc: CertificateService = Depends(get_cert_service),
):
    cluster_bindings, namespace_bindings = await asyncio.gather(
        run_sync(rbac_svc._cluster_bindings_for, user.username),
        run_sync(rbac_svc._namespace_bindings_for, user.username),
    )

    cert_info = None
    try:
        record = await run_sync(cert_svc.get_user, user.username)
        cert_info = {
            "cert_expiry": record.get("cert_expiry"),
            "created_at": record.get("created_at"),
            "imported": record.get("imported", False),
            "groups": record.get("groups", []),
        }
    except UserNotFoundError:
        pass

    return {
        "username": user.username,
        "role": user.role,
        "cert_info": cert_info,
        "cluster_bindings": cluster_bindings,
        "namespace_bindings": namespace_bindings,
    }
