"""Audit log: append-only record of administrative mutations.

Revision ID: 0003_audit_log
Revises: 0002_local_user_ldap_tracking
Create Date: 2026-07-28

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_audit_log"
down_revision: str | None = "0002_local_user_ldap_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(253), nullable=True),
        sa.Column("actor_role", sa.String(16), nullable=True),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
    )
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_timestamp", table_name="audit_log")
    op.drop_table("audit_log")
