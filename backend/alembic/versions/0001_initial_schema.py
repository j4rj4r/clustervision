"""Initial schema — the six tables introduced by the ConfigMap/Secret ->
PostgreSQL migration, as they existed before LDAP support.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-28

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("requester", sa.String(253), nullable=False),
        sa.Column("target_username", sa.String(253), nullable=False),
        sa.Column("user_kind", sa.String(32), nullable=False),
        sa.Column("sa_namespace", sa.String(63), nullable=True),
        sa.Column("role_name", sa.String(253), nullable=False),
        sa.Column("role_kind", sa.String(32), nullable=False),
        sa.Column("namespace", sa.String(63), nullable=True),
        sa.Column("ttl_minutes", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(253), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("binding_name", sa.String(253), nullable=True),
    )
    op.create_index("ix_access_requests_requester", "access_requests", ["requester"])
    op.create_index("ix_access_requests_status", "access_requests", ["status"])
    op.create_index("ix_access_requests_expires_at", "access_requests", ["expires_at"])

    op.create_table(
        "local_users",
        sa.Column("username", sa.String(253), primary_key=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
    )

    op.create_table(
        "managed_users",
        sa.Column("name", sa.String(253), primary_key=True),
        sa.Column("namespace", sa.String(63), primary_key=True, server_default="default"),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("groups_csv", sa.String(1000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("csr_name", sa.String(253), nullable=True),
        sa.Column("cert_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "token_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user", sa.String(253), nullable=False),
        sa.Column("user_type", sa.String(32), nullable=False),
        sa.Column("namespace", sa.String(63), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_token_history_generated_at", "token_history", ["generated_at"])

    op.create_table(
        "registered_clusters",
        sa.Column("name", sa.String(63), primary_key=True),
        sa.Column("api_url", sa.String(500), nullable=False),
        sa.Column("ca_data", sa.String, nullable=False),
        sa.Column("token", sa.String, nullable=False),
    )

    op.create_table(
        "vault_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("addr", sa.String(500), nullable=False, server_default=""),
        sa.Column("token", sa.String, nullable=False, server_default=""),
        sa.Column("mount", sa.String(255), nullable=False, server_default="secret"),
        sa.Column("base_path", sa.String(500), nullable=False, server_default="clustervision/users"),
        sa.Column("namespace", sa.String(255), nullable=False, server_default=""),
        sa.Column("tls_skip_verify", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("vault_config")
    op.drop_table("registered_clusters")
    op.drop_index("ix_token_history_generated_at", table_name="token_history")
    op.drop_table("token_history")
    op.drop_table("managed_users")
    op.drop_table("local_users")
    op.drop_index("ix_access_requests_expires_at", table_name="access_requests")
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_index("ix_access_requests_requester", table_name="access_requests")
    op.drop_table("access_requests")
