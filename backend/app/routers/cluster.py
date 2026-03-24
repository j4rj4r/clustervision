import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
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


@router.get("/bootstrap-script", response_class=PlainTextResponse)
async def bootstrap_script(request: Request, name: str = Query(..., description="Name to give this cluster in ClusterVision")):
    base_url = str(request.base_url).rstrip("/")
    script = f"""#!/bin/sh
# ClusterVision — bootstrap agent on a remote cluster
# Run this script with a kubeconfig targeting the cluster you want to add.
set -e

CLUSTER_NAME="{name}"
CLUSTERVISION_URL="{base_url}"
NAMESPACE="clustervision"
SA_NAME="clustervision-agent"

echo "→ Creating namespace $NAMESPACE..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "→ Creating ServiceAccount, ClusterRole, ClusterRoleBinding and token Secret..."
kubectl apply -f - <<MANIFEST
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SA_NAME
  namespace: $NAMESPACE
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: clustervision-agent
rules:
- apiGroups: ["certificates.k8s.io"]
  resources: ["certificatesigningrequests"]
  verbs: ["get", "list", "watch", "create", "delete"]
- apiGroups: ["certificates.k8s.io"]
  resources: ["certificatesigningrequests/approval"]
  verbs: ["update", "patch"]
- apiGroups: ["certificates.k8s.io"]
  resources: ["signers"]
  resourceNames: ["kubernetes.io/kube-apiserver-client"]
  verbs: ["approve"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["clusterroles", "clusterrolebindings", "roles", "rolebindings"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["serviceaccounts"]
  verbs: ["get", "list", "watch", "create", "delete"]
- apiGroups: [""]
  resources: ["serviceaccounts/token"]
  verbs: ["create"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch", "create", "delete"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: clustervision-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: clustervision-agent
subjects:
- kind: ServiceAccount
  name: $SA_NAME
  namespace: $NAMESPACE
---
apiVersion: v1
kind: Secret
metadata:
  name: clustervision-agent-token
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/service-account.name: $SA_NAME
type: kubernetes.io/service-account-token
MANIFEST

echo "→ Waiting for token to be populated..."
for i in $(seq 1 10); do
  TOKEN=$(kubectl get secret clustervision-agent-token -n "$NAMESPACE" -o jsonpath='{{.data.token}}' 2>/dev/null || true)
  [ -n "$TOKEN" ] && break
  sleep 2
done

if [ -z "$TOKEN" ]; then
  echo "ERROR: Token not available after 20s. Check your cluster." >&2
  exit 1
fi

CA=$(kubectl get secret clustervision-agent-token -n "$NAMESPACE" -o jsonpath='{{.data.ca\\.crt}}')
API_URL=$(kubectl config view --minify -o jsonpath='{{.clusters[0].cluster.server}}')

echo "→ Registering cluster '$CLUSTER_NAME' in ClusterVision..."
curl -sf -X POST "$CLUSTERVISION_URL/api/cluster/clusters" \\
  -H "Content-Type: application/json" \\
  -d "{\\"name\\":\\"$CLUSTER_NAME\\",\\"api_url\\":\\"$API_URL\\",\\"ca_data\\":\\"$CA\\",\\"token\\":\\"$TOKEN\\"}"

echo ""
echo "✓ Cluster '$CLUSTER_NAME' successfully registered in ClusterVision."
"""
    return script


@router.delete("/clusters/{name}", status_code=204)
async def remove_cluster(name: str):
    loop = asyncio.get_event_loop()
    svc = get_cluster_service()
    try:
        await loop.run_in_executor(None, svc.remove_cluster, name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
