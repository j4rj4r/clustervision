from pydantic import BaseModel


class AuditLogEntryRead(BaseModel):
    id: str
    timestamp: str
    actor: str | None = None
    actor_role: str | None = None
    method: str
    path: str
    status_code: int
    payload: dict | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogEntryRead]
    total: int
