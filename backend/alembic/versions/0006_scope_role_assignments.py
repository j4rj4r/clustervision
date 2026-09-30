"""Scope-based role assignments: replace the single global local_users.role
(admin/viewer) with per-scope roles (per real cluster, plus the "_instance"
pseudo-scope for instance-wide settings), so an account can be e.g. admin on
one cluster and have no access at all to another.

Every existing account's current global role is copied onto every scope
that exists at migration time (_instance, local, and each registered
cluster) so nobody loses access on deploy — see ScopeRoleAssignment in
app/db/models.py.

Revision ID: 0006_scope_role_assignments
Revises: 0005_login_attempts
Create Date: 2026-09-30

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_scope_role_assignments"
down_revision: str | None = "0005_login_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scope_role_assignments",
        sa.Column("username", sa.String(253), sa.ForeignKey("local_users.username", ondelete="CASCADE"), primary_key=True),
        sa.Column("scope", sa.String(63), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
    )

    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT username, role FROM local_users")).fetchall()
    cluster_names = [row[0] for row in conn.execute(sa.text("SELECT name FROM registered_clusters")).fetchall()]
    scopes = ["_instance", "local", *cluster_names]

    if users:
        assignments_table = sa.table(
            "scope_role_assignments",
            sa.column("username", sa.String),
            sa.column("scope", sa.String),
            sa.column("role", sa.String),
        )
        op.bulk_insert(
            assignments_table,
            [
                {"username": username, "scope": scope, "role": role}
                for username, role in users
                for scope in scopes
            ],
        )

    op.drop_column("local_users", "role")


def downgrade() -> None:
    op.add_column("local_users", sa.Column("role", sa.String(16), nullable=False, server_default="viewer"))

    # The old model only had admin/viewer — operator/approver collapse to
    # viewer (the closest safe equivalent) on downgrade.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT username, role FROM scope_role_assignments WHERE scope = '_instance'")
    ).fetchall()
    for username, role in rows:
        conn.execute(
            sa.text("UPDATE local_users SET role = :role WHERE username = :username"),
            {"role": "admin" if role == "admin" else "viewer", "username": username},
        )

    op.alter_column("local_users", "role", server_default=None)

    op.drop_table("scope_role_assignments")
