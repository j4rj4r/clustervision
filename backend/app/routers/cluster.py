import asyncio
from fastapi import APIRouter, Depends
from kubernetes import client

from ..core.kubernetes_client import get_api_client, get_version_api

router = APIRouter(prefix="/api/cluster", tags=["cluster"])


@router.get("/info")
async def cluster_info(api_client: client.ApiClient = Depends(get_api_client)):
    loop = asyncio.get_event_loop()
    version_api = get_version_api(api_client)
    version = await loop.run_in_executor(None, version_api.get_code)
    return {
        "git_version": version.git_version,
        "platform": version.platform,
        "go_version": version.go_version,
    }
