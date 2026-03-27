from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..models.kubeconfig import KubeconfigRequest
from ..models.user import UserType
from ..services.certificate_service import CertificateService
from ..services.service_account_service import ServiceAccountService
from ..services.kubeconfig_service import KubeconfigService
from ..dependencies import get_cert_service, get_sa_service, get_kubeconfig_service, get_token_service
from ..services.token_service import TokenService
from ..core.async_utils import run_sync

router = APIRouter(prefix="/api/kubeconfig", tags=["kubeconfig"])


@router.post("/generate")
async def generate_kubeconfig(
    payload: KubeconfigRequest,
    cert_svc: CertificateService = Depends(get_cert_service),
    sa_svc: ServiceAccountService = Depends(get_sa_service),
    kc_svc: KubeconfigService = Depends(get_kubeconfig_service),
    token_svc: TokenService = Depends(get_token_service),
):
    if payload.user_type == UserType.certificate:
        if not payload.private_key_pem:
            raise HTTPException(
                status_code=400,
                detail="private_key_pem is required for certificate users",
            )
        certificate_pem = await run_sync(cert_svc.get_certificate_pem, payload.username)
        kubeconfig_yaml = await run_sync(
            kc_svc.generate_for_cert_user,
            payload.username,
            certificate_pem,
            payload.private_key_pem,
            payload.namespace,
        )
        effective_namespace = payload.namespace or "default"
    else:
        user = await run_sync(sa_svc.get_user, payload.username, "default")
        effective_namespace = user.get("namespace", "default")
        kubeconfig_yaml = await run_sync(
            kc_svc.generate_for_service_account,
            payload.username,
            effective_namespace,
            payload.namespace,
        )

    try:
        await run_sync(token_svc.record_generation, payload.username, payload.user_type.value, effective_namespace)
    except Exception:
        pass  # history recording must not fail the generation

    return Response(
        content=kubeconfig_yaml,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f'attachment; filename="{payload.username}-kubeconfig.yaml"'
        },
    )
