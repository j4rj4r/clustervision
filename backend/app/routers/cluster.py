import base64
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from kubernetes import client
from pydantic import BaseModel, field_validator

from ..config import get_settings
from ..core.async_utils import run_sync
from ..core.auth import create_register_token, decode_token
from ..core.dependencies import require_admin
from ..core.kubernetes_client import get_version_api
from ..dependencies import get_api_client
from ..models.auth import UserInfo
from ..services.cluster_service import ClusterConnectionError, get_cluster_service

_CLUSTER_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,63}$')

router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])

# Routes on this router are mounted WITHOUT the auth_gate dependency —
# they carry their own authentication (bootstrap register token).
public_router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])

_register_bearer = HTTPBearer(auto_error=False)


# ── Models ───────────────────────────────────────────────────────────────────

class ClusterAdd(BaseModel):
    name: str
    api_url: str
    ca_data: str   # base64-encoded PEM CA certificate
    token: str     # ServiceAccount bearer token

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _CLUSTER_NAME_RE.match(v):
            raise ValueError("name must be 1-63 alphanumeric characters, hyphens or underscores")
        return v

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        try:
            parsed = urlparse(v)
        except Exception:
            raise ValueError("api_url must be a valid URL")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("api_url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("api_url must include a host")
        return v

    @field_validator("ca_data")
    @classmethod
    def validate_ca_data(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("ca_data must be valid base64")
        return v


class ClusterInfo(BaseModel):
    name: str
    api_url: str
    is_local: bool = False


# ── Current cluster info ──────────────────────────────────────────────────────

@router.get(
    "/info",
    summary="Get active cluster info",
    description="Returns the Kubernetes server version of the currently active cluster.",
)
async def cluster_info(api_client: client.ApiClient = Depends(get_api_client)):
    version_api = get_version_api(api_client)
    version = await run_sync(version_api.get_code)
    return {
        "git_version": version.git_version,
        "platform": version.platform,
        "go_version": version.go_version,
    }


# ── Multi-cluster registry ────────────────────────────────────────────────────

@router.get("/clusters", summary="List registered clusters")
async def list_clusters():
    svc = get_cluster_service()
    remote = await run_sync(svc.list_clusters)
    return [{"name": "local", "api_url": "", "is_local": True}, *remote]


@router.post(
    "/clusters",
    status_code=201,
    summary="Register a remote cluster",
    description="Add a remote cluster by providing its API URL, CA certificate (base64 PEM) and a ServiceAccount bearer token.",
)
async def add_cluster(payload: ClusterAdd):
    svc = get_cluster_service()
    try:
        return await run_sync(svc.add_cluster, payload.name, payload.api_url, payload.ca_data, payload.token)
    except ClusterConnectionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@public_router.post(
    "/register",
    status_code=201,
    summary="Register a remote cluster (bootstrap token)",
    description=(
        "Same as `POST /clusters` but authenticated with the short-lived registration token "
        "embedded in the bootstrap script instead of an admin session. "
        "The token is scoped to a single cluster name."
    ),
)
async def register_cluster(
    payload: ClusterAdd,
    credentials: HTTPAuthorizationCredentials | None = Depends(_register_bearer),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bootstrap token")
    token_payload = decode_token(credentials.credentials, expected_type="cluster_register")
    if token_payload.get("sub") != payload.name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap token was issued for a different cluster name",
        )
    svc = get_cluster_service()
    try:
        return await run_sync(svc.add_cluster, payload.name, payload.api_url, payload.ca_data, payload.token)
    except ClusterConnectionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/bootstrap-script",
    response_class=PlainTextResponse,
    summary="Get bootstrap shell script",
    description=(
        "Returns a shell script that, when run against a remote cluster with `kubectl`, "
        "creates the ClusterVision ServiceAccount with the required RBAC permissions and "
        "registers the cluster automatically via the API. "
        "The script embeds a registration token valid for 1 hour, scoped to the given cluster name."
    ),
)
async def bootstrap_script(
    request: Request,
    name: str = Query(..., description="Name to give this cluster in ClusterVision"),
    _: UserInfo = Depends(require_admin),
):
    if not _CLUSTER_NAME_RE.match(name):
        raise HTTPException(
            status_code=422,
            detail="Cluster name must be 1-63 alphanumeric characters, hyphens or underscores."
        )
    settings = get_settings()
    base_url = settings.public_url.rstrip("/") if settings.public_url else str(request.base_url).rstrip("/")
    register_token = create_register_token(name)
    script = f"""#!/bin/sh
# ClusterVision — bootstrap agent on a remote cluster
# Run this script with a kubeconfig targeting the cluster you want to add.
set -e

CLUSTER_NAME="{name}"
CLUSTERVISION_URL="{base_url}"
REGISTER_TOKEN="{register_token}"
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
  TOKEN_B64=$(kubectl get secret clustervision-agent-token -n "$NAMESPACE" -o jsonpath='{{.data.token}}' 2>/dev/null || true)
  [ -n "$TOKEN_B64" ] && break
  sleep 2
done

if [ -z "$TOKEN_B64" ]; then
  echo "ERROR: Token not available after 20s. Check your cluster." >&2
  exit 1
fi

# The registration API expects the raw JWT but .data.token is base64-encoded.
# Decode through kubectl — the base64 CLI flags differ between GNU and BSD.
TOKEN=$(kubectl get secret clustervision-agent-token -n "$NAMESPACE" -o go-template='{{{{.data.token | base64decode}}}}')
CA=$(kubectl get secret clustervision-agent-token -n "$NAMESPACE" -o jsonpath='{{.data.ca\\.crt}}')
API_URL=$(kubectl config view --minify -o jsonpath='{{.clusters[0].cluster.server}}')

echo "→ Registering cluster '$CLUSTER_NAME' in ClusterVision..."
curl -sfS -X POST "$CLUSTERVISION_URL/api/v1/cluster/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $REGISTER_TOKEN" \
  -d '{{"name":"'"$CLUSTER_NAME"'","api_url":"'"$API_URL"'","ca_data":"'"$CA"'","token":"'"$TOKEN"'"}}'

echo ""
echo "✓ Cluster '$CLUSTER_NAME' successfully registered in ClusterVision."
"""
    return script


@router.delete("/clusters/{name}", status_code=204, summary="Remove a registered cluster")
async def remove_cluster(name: str):
    svc = get_cluster_service()
    try:
        await run_sync(svc.remove_cluster, name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
