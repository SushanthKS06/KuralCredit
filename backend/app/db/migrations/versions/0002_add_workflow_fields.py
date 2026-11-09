"""Add workflow_id and workflow_version fields.

Revision ID: 0002_add_workflow_fields
Revises: 0001_initial_schema
Create Date: 2026-11-09 18:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_workflow_fields"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "applications" in tables:
        cols = {c["name"] for c in inspector.get_columns("applications")}
        if "workflow_id" not in cols:
            op.add_column(
                "applications",
                sa.Column(
                    "workflow_id",
                    sa.String(60),
                    nullable=False,
                    server_default="loan_application",
                ),
            )
        if "workflow_version" not in cols:
            op.add_column(
                "applications",
                sa.Column(
                    "workflow_version",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                ),
            )

    if "sessions" in tables:
        cols = {c["name"] for c in inspector.get_columns("sessions")}
        if "workflow_id" not in cols:
            op.add_column(
                "sessions",
                sa.Column("workflow_id", sa.String(60), nullable=True),
            )


def downgrade() -> None:
    op.drop_column("sessions", "workflow_id")
    op.drop_column("applications", "workflow_version")
    op.drop_column("applications", "workflow_id")
