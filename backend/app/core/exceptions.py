import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from kubernetes.client.exceptions import ApiException

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User '{username}' not found")


class UserAlreadyExistsError(Exception):
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"User '{username}' already exists")


class CertificateTimeoutError(Exception):
    def __init__(self, csr_name: str):
        super().__init__(f"CSR '{csr_name}' was not signed within timeout")


class ImportedUserError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def k8s_exception_to_http(exc: ApiException) -> HTTPException:
    if exc.status == 404:
        return HTTPException(status_code=404, detail=exc.reason)
    if exc.status == 409:
        return HTTPException(status_code=409, detail="Resource already exists")
    if exc.status == 403:
        return HTTPException(status_code=403, detail="Forbidden: insufficient permissions")
    return HTTPException(status_code=500, detail=f"Kubernetes API error: {exc.reason}")


async def kubernetes_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    logger.error("Kubernetes API error %s %s: %s", exc.status, exc.reason, exc.body)
    http_exc = k8s_exception_to_http(exc)
    return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})


async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def user_exists_handler(request: Request, exc: UserAlreadyExistsError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def imported_user_handler(request: Request, exc: ImportedUserError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
