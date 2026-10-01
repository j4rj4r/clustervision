import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.access")

# gunicorn's --access-logfile has no effect with UvicornWorker: requests are
# handled entirely inside uvicorn's own ASGI server loop, which never calls
# back into gunicorn's WSGI-style access-logging code path. Without this,
# there is no per-request log line in kubectl logs at all — not even a
# generic one — making every production issue invisible until something
# raises hard enough to hit one of our own explicit logger.error() calls.
class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        cluster = request.query_params.get("cluster", "")
        logger.info(
            "%s %s%s -> %s (%.1fms)",
            request.method,
            request.url.path,
            f" [cluster={cluster}]" if cluster else "",
            response.status_code,
            duration_ms,
        )
        return response
