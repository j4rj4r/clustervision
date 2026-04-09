import urllib3
from kubernetes import client, config
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Connect timeout: time to establish a TCP connection to the API server.
# Read timeout: max time to wait for a response after the request is sent.
_K8S_TIMEOUT = urllib3.Timeout(connect=10, read=30)


@lru_cache(maxsize=1)
def get_local_api_client() -> client.ApiClient:
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig")
    api_client = client.ApiClient()
    api_client.rest_client.pool_manager.connection_pool_kw["timeout"] = _K8S_TIMEOUT
    return api_client


# Keep backward-compat alias
get_api_client = get_local_api_client


def get_version_api(api_client: client.ApiClient) -> client.VersionApi:
    return client.VersionApi(api_client)
