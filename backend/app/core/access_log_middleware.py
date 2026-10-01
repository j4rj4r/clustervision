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
#
# uvicorn's own "uvicorn.access" logger is deliberately silenced instead of
# just left alongside this one (see logging.json's empty "gunicorn.access"
# handlers — UvicornWorker copies that handler list onto uvicorn.access at
# worker boot): without that, every request would be logged twice per line,
# once here with structured fields and once as uvicorn's unstructured
# "<ip> - "<method> <path> HTTP/1.1" <status>" string, via two different
# loggers that both happen to write to the same stdout handler.
class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        cluster = request.query_params.get("cluster", "")
        # Extra fields land as their own JSON keys (see JsonFormatter), so a
        # log tool can filter/aggregate on http_status, duration_ms, etc.
        # directly instead of regex-parsing the message string.
        logger.info(
            "%s %s%s -> %s (%.1fms)",
            request.method,
            request.url.path,
            f" [cluster={cluster}]" if cluster else "",
            response.status_code,
            duration_ms,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "client_ip": request.client.host if request.client else None,
                **({"cluster": cluster} if cluster else {}),
            },
        )
        return response
