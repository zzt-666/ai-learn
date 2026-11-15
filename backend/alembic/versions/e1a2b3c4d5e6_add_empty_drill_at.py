"""add empty_drill_at for auto downgrade

Revision ID: e1a2b3c4d5e6
Revises: d9e4a13c6f32
Create Date: 2026-11-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1a2b3c4d5e6"
down_revision = "d9e4a13c6f32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("empty_drill_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "empty_drill_at")
