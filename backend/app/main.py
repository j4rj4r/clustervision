from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes.client.exceptions import ApiException

from .core.exceptions import (
    kubernetes_exception_handler,
    user_not_found_handler,
    user_exists_handler,
    UserNotFoundError,
    UserAlreadyExistsError,
)
from .config import get_settings
from .core.kubernetes_client import get_api_client
from .routers import users, rbac, kubeconfig, cluster, tokens

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly initialize the K8s client on startup to surface config errors early
    try:
        get_api_client()
        logger.info("Kubernetes client initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize Kubernetes client: {e}")
    yield


openapi_tags = [
    {
        "name": "users",
        "description": (
            "Manage ClusterVision users. Two types are supported: "
            "**certificate** (X.509 client cert, identity in CN/O fields) and "
            "**service_account** (Kubernetes ServiceAccount with a long-lived token). "
            "Deleting a user also removes all managed role bindings."
        ),
    },
    {
        "name": "rbac",
        "description": (
            "Manage Kubernetes RBAC objects: ClusterRoles, namespaced Roles, "
            "ClusterRoleBindings, RoleBindings. Also exposes user-centric helpers "
            "to assign/revoke roles and simulate access checks."
        ),
    },
    {
        "name": "kubeconfig",
        "description": (
            "Generate kubeconfig files ready to use with `kubectl`. "
            "For certificate users the private key PEM must be supplied at generation time "
            "(it is never stored server-side). For ServiceAccounts the token is fetched automatically."
        ),
    },
    {
        "name": "tokens",
        "description": (
            "Kubeconfig generation history and ServiceAccount token management "
            "(list, revoke, rotate)."
        ),
    },
    {
        "name": "cluster",
        "description": (
            "Multi-cluster registry. Register remote clusters via a bootstrap script, "
            "list connected clusters, and query the active cluster version."
        ),
    },
]

app = FastAPI(
    title="ClusterVision",
    summary="Kubernetes user & RBAC management API",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    description="""
ClusterVision lets you **create, manage and delete** Kubernetes users (X.509 certificates
and ServiceAccounts) and their RBAC permissions through a single REST API.

## Authentication
No authentication is built into the API itself — access should be restricted at the
network layer (ingress, NetworkPolicy) or via a reverse-proxy.

## User types
| Type | Auth method | Revocation |
|------|-------------|------------|
| `certificate` | TLS client certificate (X.509) | Soft — remove bindings; cert valid until expiry |
| `service_account` | Bearer token | Immediate — delete the token Secret |

## Managed naming convention
ClusterVision names every binding it creates `clustervision-{username}-{role}`.
This prefix is used to identify and clean up bindings on user deletion.
""",
    version=get_settings().app_version,
    openapi_tags=openapi_tags,
    lifespan=lifespan,
    license_info={"name": "MIT"},
    contact={"name": "ClusterVision", "url": "https://github.com/j4rj4r/clustervision"},
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiException, kubernetes_exception_handler)
app.add_exception_handler(UserNotFoundError, user_not_found_handler)
app.add_exception_handler(UserAlreadyExistsError, user_exists_handler)

app.include_router(users.router)
app.include_router(rbac.router)
app.include_router(kubeconfig.router)
app.include_router(cluster.router)
app.include_router(tokens.router)


@app.get("/health")
def health():
    return {"status": "ok"}
