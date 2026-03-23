import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from kubernetes import client

from ..core.kubernetes_client import get_local_api_client, get_version_api
from ..services.cluster_service import get_cluster_service
from ..dependencies import get_api_client


router = APIRouter(prefix="/api/cluster", tags=["cluster"])


# ── Models ───────────────────────────────────────────────────────────────────

class ClusterAdd(BaseModel):
    name: str
    api_url: str
    ca_data: str   # base64-encoded PEM CA certificate
    token: str     # ServiceAccount bearer token


class ClusterInfo(BaseModel):
    name: str
    api_url: str
    is_local: bool = False


# ── Current cluster info ──────────────────────────────────────────────────────

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


# ── Multi-cluster registry ────────────────────────────────────────────────────

@router.get("/clusters")
async def list_clusters():
    loop = asyncio.get_event_loop()
    svc = get_cluster_service()
    remote = await loop.run_in_executor(None, svc.list_clusters)
    return [{"name": "local", "api_url": "", "is_local": True}] + remote


@router.post("/clusters", status_code=201)
async def add_cluster(payload: ClusterAdd):
    loop = asyncio.get_event_loop()
    svc = get_cluster_service()
    try:
        return await loop.run_in_executor(
            None, svc.add_cluster, payload.name, payload.api_url, payload.ca_data, payload.token
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/clusters/{name}", status_code=204)
async def remove_cluster(name: str):
    loop = asyncio.get_event_loop()
    svc = get_cluster_service()
    try:
        await loop.run_in_executor(None, svc.remove_cluster, name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
