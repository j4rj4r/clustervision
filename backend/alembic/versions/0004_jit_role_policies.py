"""JIT role policies: per-role eligibility and TTL cap overrides for access requests.

Revision ID: 0004_jit_role_policies
Revises: 0003_audit_log
Create Date: 2026-07-29

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_jit_role_policies"
down_revision: str | None = "0003_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jit_role_policies",
        sa.Column("role_kind", sa.String(32), primary_key=True),
        sa.Column("role_name", sa.String(253), primary_key=True),
        sa.Column("eligible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("max_ttl_minutes", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("jit_role_policies")
