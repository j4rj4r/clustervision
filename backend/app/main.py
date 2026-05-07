from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from kubernetes.client.exceptions import ApiException

from .core.exceptions import (
    kubernetes_exception_handler,
    user_not_found_handler,
    user_exists_handler,
    imported_user_handler,
    UserNotFoundError,
    UserAlreadyExistsError,
    ImportedUserError,
)
from .config import get_settings
from .core.kubernetes_client import get_api_client
from .core.dependencies import auth_gate
from .routers import users, rbac, kubeconfig, cluster, tokens
from .routers import auth as auth_router
from .routers import vault_admin as vault_admin_router
from .services.auth_service import ensure_default_admin

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly initialize the K8s client on startup to surface config errors early
    try:
        get_api_client()
        logger.info("Kubernetes client initialized successfully")
    except Exception as e:
        logger.warning("Could not initialize Kubernetes client: %s", e)
    ensure_default_admin()
    from .services.vault_service import init_vault_from_env
    init_vault_from_env()
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
JWT-based. POST `/api/v1/auth/login` to get an access token (15 min),
renewed automatically via an httpOnly refresh cookie (7 days).
Viewers can read; admins can read and write.

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

app.add_middleware(GZipMiddleware, minimum_size=1000)

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
app.add_exception_handler(ImportedUserError, imported_user_handler)

_auth_dep = [Depends(auth_gate)]

app.include_router(auth_router.router)
app.include_router(users.router,      dependencies=_auth_dep)
app.include_router(rbac.router,       dependencies=_auth_dep)
app.include_router(kubeconfig.router, dependencies=_auth_dep)
app.include_router(cluster.router,    dependencies=_auth_dep)
app.include_router(tokens.router,        dependencies=_auth_dep)
app.include_router(vault_admin_router.router, dependencies=_auth_dep)


@app.get("/health")
def health():
    return {"status": "ok"}
