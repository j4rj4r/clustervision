from fastapi import Depends, Query
from kubernetes import client

from .core.kubernetes_client import get_local_api_client
from .services.certificate_service import CertificateService
from .services.cluster_service import get_cluster_service
from .services.kubeconfig_service import KubeconfigService
from .services.rbac_service import RbacService
from .services.service_account_service import ServiceAccountService
from .services.token_service import TokenService


def get_api_client(cluster: str = Query("local")) -> client.ApiClient:
    if cluster == "local":
        return get_local_api_client()
    return get_cluster_service().get_api_client(cluster)


def get_cert_service(api_client: client.ApiClient = Depends(get_api_client)) -> CertificateService:
    return CertificateService(api_client)


def get_sa_service(api_client: client.ApiClient = Depends(get_api_client)) -> ServiceAccountService:
    return ServiceAccountService(api_client)


def get_rbac_service(api_client: client.ApiClient = Depends(get_api_client)) -> RbacService:
    return RbacService(api_client)


def get_kubeconfig_service(api_client: client.ApiClient = Depends(get_api_client)) -> KubeconfigService:
    return KubeconfigService(api_client)


def get_token_service(api_client: client.ApiClient = Depends(get_api_client)) -> TokenService:
    return TokenService(api_client)
