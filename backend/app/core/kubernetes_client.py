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


def get_version_api(api_client: client.ApiClient) -> client.VersionApi:
    return client.VersionApi(api_client)
