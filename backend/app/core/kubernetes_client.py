from kubernetes import client, config
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_api_client() -> client.ApiClient:
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig")
    return client.ApiClient()


def get_core_v1(api_client: client.ApiClient = None) -> client.CoreV1Api:
    return client.CoreV1Api(api_client or get_api_client())


def get_rbac_v1(api_client: client.ApiClient = None) -> client.RbacAuthorizationV1Api:
    return client.RbacAuthorizationV1Api(api_client or get_api_client())


def get_certs_v1(api_client: client.ApiClient = None) -> client.CertificatesV1Api:
    return client.CertificatesV1Api(api_client or get_api_client())


def get_version_api(api_client: client.ApiClient = None) -> client.VersionApi:
    return client.VersionApi(api_client or get_api_client())
