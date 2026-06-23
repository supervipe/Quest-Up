"""Allow community posts without photos.

Revision ID: 20260622_0003
Revises: 20260613_0002
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260622_0003"
down_revision: str | None = "20260613_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("community_posts")
    }
    photo_column = columns.get("photo_url")
    if photo_column and not photo_column["nullable"]:
        op.alter_column(
            "community_posts",
            "photo_url",
            existing_type=sa.Text(),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("community_posts")
    }
    photo_column = columns.get("photo_url")
    if photo_column and photo_column["nullable"]:
        op.alter_column(
            "community_posts",
            "photo_url",
            existing_type=sa.Text(),
            nullable=False,
        )
