from contextlib import asynccontextmanager
import asyncio
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
from .routers import users, rbac, kubeconfig, cluster, tokens, profile
from .routers import auth as auth_router
from .routers import drift as drift_router
from .routers import access_requests as access_requests_router
from .routers import vault_admin as vault_admin_router
from .services.auth_service import ensure_default_admin

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


async def _drift_background(svc):
    """Run periodic drift scan every 60s + real-time watch in background."""
    async def _periodic():
        while True:
            await asyncio.sleep(60)
            try:
                new = await run_sync(svc.scan)
                if new:
                    logger.warning("Drift scan found %d new event(s)", len(new))
            except Exception as e:
                logger.warning("Drift scan error: %s", e)

    await asyncio.gather(_periodic(), svc.watch_loop())


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_api_client()
        logger.info("Kubernetes client initialized successfully")
    except Exception as e:
        logger.warning("Could not initialize Kubernetes client: %s", e)
    ensure_default_admin()
    from .services.vault_service import init_vault_from_env
    init_vault_from_env()

    try:
        from .routers.drift import get_drift_service
        from .core.async_utils import run_sync
        drift_svc = get_drift_service()
        drift_task = asyncio.create_task(_drift_background(drift_svc))
    except Exception as e:
        logger.warning("Could not start drift watcher: %s", e)
        drift_task = None

    yield

    if drift_task:
        drift_task.cancel()


openapi_tags = [
    {
        "name": "auth",
        "description": (
            "Authentication endpoints. POST `/login` to obtain an access token (15 min JWT) "
            "and an httpOnly refresh cookie (7 days). Use `/refresh` to silently renew the "
            "access token. Admin-only endpoints for managing ClusterVision users are also here."
        ),
    },
    {
        "name": "users",
        "description": (
            "Manage ClusterVision-tracked Kubernetes users. Two types: "
            "**certificate** (X.509 client cert, CN=username, O=groups) and "
            "**service_account** (Kubernetes ServiceAccount + long-lived token Secret). "
            "Deleting a user also removes all `clustervision-{username}-*` bindings. "
            "Certificate users support rotation via `POST /{username}/renew-certificate`."
        ),
    },
    {
        "name": "rbac",
        "description": (
            "Manage Kubernetes RBAC: ClusterRoles, namespaced Roles, ClusterRoleBindings, RoleBindings. "
            "User-centric helpers: assign/revoke roles, who-has-access view, SubjectAccessReview simulator."
        ),
    },
    {
        "name": "kubeconfig",
        "description": (
            "Generate kubeconfig files ready to use with `kubectl`. "
            "For certificate users the private key PEM must be supplied — it is never stored server-side "
            "(or stored in Vault if the integration is enabled). "
            "For ServiceAccounts the token is fetched automatically from the cluster."
        ),
    },
    {
        "name": "tokens",
        "description": (
            "Kubeconfig generation audit trail and ServiceAccount token management "
            "(list, revoke, rotate long-lived token Secrets)."
        ),
    },
    {
        "name": "cluster",
        "description": (
            "Multi-cluster registry. Register remote clusters via a bootstrap script, "
            "list connected clusters, and query the active cluster version."
        ),
    },
    {
        "name": "profile",
        "description": (
            "Self-service endpoint. Returns the authenticated user's own identity, "
            "certificate info, and all K8s bindings — no admin rights required."
        ),
    },
    {
        "name": "access-requests",
        "description": (
            "Approval workflow for role requests. Any authenticated user can submit a request "
            "(role, namespace, justification). Admins approve (binding created automatically) or deny. "
            "Viewers see only their own requests; admins see all."
        ),
    },
    {
        "name": "drift",
        "description": (
            "RBAC drift detection. Watches ClusterVision-managed bindings for external modifications "
            "and runs periodic scans for label-stripped bindings. Admin-only."
        ),
    },
    {
        "name": "admin",
        "description": (
            "Admin-only runtime configuration. Currently: Vault integration (configure, test, disable). "
            "Changes take effect immediately without a restart."
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
JWT-based. `POST /api/v1/auth/login` → access token (15 min, Bearer) + httpOnly refresh cookie (7 days).
Use **Authorize** above and enter `Bearer <token>` to authenticate in this UI.

| Role | Permissions |
|------|-------------|
| `admin` | Full read & write access to all endpoints |
| `viewer` | Read-only on GET endpoints; can submit access requests and view own profile |

## User types
| Type | Auth method | Revocation |
|------|-------------|------------|
| `certificate` | X.509 client certificate (CN=username, O=groups) | Soft — remove bindings; cert valid until expiry |
| `service_account` | Long-lived Bearer token Secret | Immediate — delete the token Secret |

## Managed naming convention
Every binding created by ClusterVision is named `clustervision-{username}-{role}`.
This prefix is used to identify, clean up, and drift-detect managed resources.

## Vault integration
When enabled, certificate private keys are written to HashiCorp Vault KV v2
instead of being returned inline. Configure at `PUT /api/v1/admin/vault/config`.
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
app.include_router(tokens.router,     dependencies=_auth_dep)
app.include_router(profile.router,    dependencies=_auth_dep)
app.include_router(drift_router.router,           dependencies=_auth_dep)
app.include_router(access_requests_router.router, dependencies=_auth_dep)
app.include_router(vault_admin_router.router,     dependencies=_auth_dep)


@app.get("/health")
def health():
    return {"status": "ok"}
