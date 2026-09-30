"""Optional link from a login account (local_users) to a managed Kubernetes
identity (managed_users) — self-service "my kubeconfig" convenience, no
permissions implication. No FK: cleanup happens explicitly when a managed
user is deleted (see app.services.auth_service.clear_links_to).

Revision ID: 0007_linked_managed_user
Revises: 0006_scope_role_assignments
Create Date: 2026-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_linked_managed_user"
down_revision: str | None = "0006_scope_role_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "local_users", sa.Column("linked_managed_user", sa.String(253), nullable=True)
    )
    op.add_column(
        "local_users",
        sa.Column("linked_managed_user_namespace", sa.String(63), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_users", "linked_managed_user_namespace")
    op.drop_column("local_users", "linked_managed_user")
