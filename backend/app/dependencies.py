from fastapi import Depends
from kubernetes import client

from .core.kubernetes_client import get_api_client
from .services.certificate_service import CertificateService
from .services.service_account_service import ServiceAccountService
from .services.rbac_service import RbacService
from .services.kubeconfig_service import KubeconfigService


def get_cert_service(api_client: client.ApiClient = Depends(get_api_client)) -> CertificateService:
    return CertificateService(api_client)


def get_sa_service(api_client: client.ApiClient = Depends(get_api_client)) -> ServiceAccountService:
    return ServiceAccountService(api_client)


def get_rbac_service(api_client: client.ApiClient = Depends(get_api_client)) -> RbacService:
    return RbacService(api_client)


def get_kubeconfig_service(api_client: client.ApiClient = Depends(get_api_client)) -> KubeconfigService:
    return KubeconfigService(api_client)
