"""Login attempts: persistent rate-limit log for /auth/login, replacing the
in-memory per-process bucket so the limit is shared across backend replicas
and survives pod restarts.

Revision ID: 0005_login_attempts
Revises: 0004_jit_role_policies
Create Date: 2026-09-22

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_login_attempts"
down_revision: str | None = "0004_jit_role_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_attempts_ip", "login_attempts", ["ip"])
    op.create_index("ix_login_attempts_attempted_at", "login_attempts", ["attempted_at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempts_attempted_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_ip", table_name="login_attempts")
    op.drop_table("login_attempts")
