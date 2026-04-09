import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)

from ..models.kubeconfig import KubeconfigRequest
from ..models.user import UserType
from ..services.certificate_service import CertificateService
from ..services.service_account_service import ServiceAccountService
from ..services.kubeconfig_service import KubeconfigService
from ..dependencies import get_cert_service, get_sa_service, get_kubeconfig_service, get_token_service
from ..services.token_service import TokenService
from ..core.async_utils import run_sync

router = APIRouter(prefix="/api/v1/kubeconfig", tags=["kubeconfig"])


@router.post(
    "/generate",
    summary="Generate a kubeconfig",
    description=(
        "Generate a kubeconfig YAML file for the given user.\n\n"
        "**Certificate users** — `private_key_pem` is required (the private key returned at creation time "
        "and never stored server-side). The signed certificate is fetched from the Kubernetes CSR.\n\n"
        "**ServiceAccount users** — no private key needed. A long-lived token Secret is used if available; "
        "otherwise a one-year TokenRequest is issued.\n\n"
        "The optional `namespace` sets the default namespace in the kubeconfig context. "
        "Leave empty to omit it."
    ),
    response_description="kubeconfig file in YAML format, ready to use with `kubectl`",
    responses={
        200: {
            "content": {"application/x-yaml": {}},
            "description": "kubeconfig YAML",
        },
        400: {"description": "private_key_pem required for certificate users"},
        404: {"description": "User not found"},
    },
)
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
        user = await run_sync(sa_svc.get_user, payload.username)
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
        logger.warning("Failed to record kubeconfig generation for %s", payload.username, exc_info=True)

    return Response(
        content=kubeconfig_yaml,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f'attachment; filename="{payload.username}-kubeconfig.yaml"'
        },
    )
