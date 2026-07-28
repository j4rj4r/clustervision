"""LDAP support: track account source and last login on local_users.

Revision ID: 0002_local_user_ldap_tracking
Revises: 0001_initial_schema
Create Date: 2026-07-28

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_local_user_ldap_tracking"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("local_users", sa.Column("source", sa.String(16), nullable=False, server_default="local"))
    op.add_column("local_users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    # LDAP-provisioned accounts have no local password — auth happens against
    # the directory every time, nothing to compare locally.
    op.alter_column("local_users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("local_users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_column("local_users", "last_login_at")
    op.drop_column("local_users", "source")
