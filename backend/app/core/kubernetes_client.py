from kubernetes import client, config
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_local_api_client() -> client.ApiClient:
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig")
    return client.ApiClient()


# Keep backward-compat alias
get_api_client = get_local_api_client


# Sub-clients are cached per ApiClient instance (id-based key).
# For the local client this means a single CoreV1Api/RbacV1Api/etc. object
# is reused across all requests instead of being reconstructed each time.
_sub_client_cache: dict[int, dict] = {}


def _get_sub(api_client: client.ApiClient, key: str, factory):
    cid = id(api_client)
    if cid not in _sub_client_cache:
        _sub_client_cache[cid] = {}
    if key not in _sub_client_cache[cid]:
        _sub_client_cache[cid][key] = factory(api_client)
    return _sub_client_cache[cid][key]


def get_core_v1(api_client: client.ApiClient = None) -> client.CoreV1Api:
    c = api_client or get_api_client()
    return _get_sub(c, "core_v1", client.CoreV1Api)


def get_rbac_v1(api_client: client.ApiClient = None) -> client.RbacAuthorizationV1Api:
    c = api_client or get_api_client()
    return _get_sub(c, "rbac_v1", client.RbacAuthorizationV1Api)


def get_certs_v1(api_client: client.ApiClient = None) -> client.CertificatesV1Api:
    c = api_client or get_api_client()
    return _get_sub(c, "certs_v1", client.CertificatesV1Api)


def get_version_api(api_client: client.ApiClient = None) -> client.VersionApi:
    c = api_client or get_api_client()
    return _get_sub(c, "version", client.VersionApi)
