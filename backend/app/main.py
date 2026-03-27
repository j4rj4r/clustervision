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


app = FastAPI(
    title="ClusterVision",
    description="Kubernetes user and RBAC management API",
    version="1.0.0",
    lifespan=lifespan,
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
