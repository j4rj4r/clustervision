from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import AuditLogEntry


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def list_entries(
        self,
        limit: int = 50,
        offset: int = 0,
        actor: str | None = None,
        path_contains: str | None = None,
    ) -> tuple[list[dict], int]:
        filters = []
        if actor:
            filters.append(AuditLogEntry.actor == actor)
        if path_contains:
            filters.append(AuditLogEntry.path.contains(path_contains))

        total = self.db.scalar(select(func.count()).select_from(AuditLogEntry).where(*filters)) or 0

        stmt = (
            select(AuditLogEntry)
            .where(*filters)
            .order_by(AuditLogEntry.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        items = [row.to_dict() for row in self.db.scalars(stmt)]
        return items, total

    def export_entries(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        actor: str | None = None,
        path_contains: str | None = None,
    ) -> list[dict]:
        """Unpaginated — for CSV export, not the paginated list view."""
        filters = []
        if since:
            filters.append(AuditLogEntry.timestamp >= since)
        if until:
            filters.append(AuditLogEntry.timestamp <= until)
        if actor:
            filters.append(AuditLogEntry.actor == actor)
        if path_contains:
            filters.append(AuditLogEntry.path.contains(path_contains))

        stmt = select(AuditLogEntry).where(*filters).order_by(AuditLogEntry.timestamp)
        return [row.to_dict() for row in self.db.scalars(stmt)]
