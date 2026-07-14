"""add onboarding completed flag to user profiles

Revision ID: 20260714_0004
Revises: 20260622_0003
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_0004"
down_revision: str | None = "20260622_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "onboarding_completed" not in columns:
        op.add_column(
            "user_profiles",
            sa.Column(
                "onboarding_completed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    op.execute("UPDATE user_profiles SET onboarding_completed = true")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "onboarding_completed" in columns:
        op.drop_column("user_profiles", "onboarding_completed")
