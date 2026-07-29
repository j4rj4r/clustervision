import json
import logging
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..db.models import AuditLogEntry
from ..db.session import new_session
from .async_utils import run_sync
from .auth import decode_token

logger = logging.getLogger(__name__)

# Same set of routers gated by auth_gate in main.py, minus access-requests —
# that flow already has its own reviewer/timestamp trail on AccessRequestRecord.
# /api/v1/auth/users (not the whole /api/v1/auth prefix) covers ClusterVision
# login-account create/delete/role-change/password-reset without also
# capturing every login/refresh/logout call, which is a much higher-volume,
# different kind of event. /api/v1/access-requests/policies is the exception
# to the access-requests exclusion — policy overrides have no reviewer trail
# of their own, unlike individual request approve/deny/revoke.
_AUDITED_PREFIXES = (
    "/api/v1/rbac",
    "/api/v1/users",
    "/api/v1/tokens",
    "/api/v1/cluster",
    "/api/v1/admin",
    "/api/v1/auth/users",
    "/api/v1/access-requests/policies",
)
_AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_REDACT_KEYS = {"password", "token", "secret", "bind_password", "ca_data", "new_password", "current_password"}


def _redact(value):
    if isinstance(value, dict):
        return {k: ("***redacted***" if k.lower() in _REDACT_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _actor_from_header(auth_header: str | None) -> tuple[str | None, str | None]:
    """Best-effort — logging must never depend on/fail with the token being
    valid, that's auth_gate's job. An expired or missing token just means
    the actor is recorded as unknown."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None
    try:
        payload = decode_token(auth_header.removeprefix("Bearer "), expected_type="access")
    except Exception:
        return None, None
    return payload.get("sub"), payload.get("role")


def _write_entry(entry: AuditLogEntry) -> None:
    db = new_session()
    try:
        db.add(entry)
        db.commit()
    finally:
        db.close()


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Records every mutating request against an audited path, successful or
    not — a viewer's 403'd delete attempt is as interesting to an auditor as
    an admin's 204."""

    async def dispatch(self, request: Request, call_next):
        should_audit = request.method in _AUDITED_METHODS and request.url.path.startswith(_AUDITED_PREFIXES)

        payload = None
        if should_audit:
            body = await request.body()
            if body:
                try:
                    payload = _redact(json.loads(body))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = None

        response = await call_next(request)

        if should_audit:
            actor, actor_role = _actor_from_header(request.headers.get("authorization"))
            entry = AuditLogEntry(
                timestamp=datetime.now(UTC),
                actor=actor,
                actor_role=actor_role,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                payload=payload,
            )
            try:
                await run_sync(_write_entry, entry)
            except Exception:
                logger.exception("Failed to write audit log entry for %s %s", request.method, request.url.path)

        return response
