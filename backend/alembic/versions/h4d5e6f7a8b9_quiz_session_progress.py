"""quiz_sessions in-progress lifecycle fields

Revision ID: h4d5e6f7a8b9
Revises: g3c4d5e6f7a8
Create Date: 2026-11-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "g3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quiz_sessions",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="completed"),
    )
    op.add_column(
        "quiz_sessions",
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "quiz_sessions",
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "quiz_sessions",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_quiz_sessions_status", "quiz_sessions", ["status"], unique=False)
    op.create_index(
        "ix_quiz_sessions_knowledge_base_id",
        "quiz_sessions",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_quiz_sessions_knowledge_base_id",
        "quiz_sessions",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
    )

    op.execute(
        sa.text(
            "UPDATE quiz_sessions SET status = 'completed', "
            "updated_at = COALESCE(finished_at, created_at) "
            "WHERE updated_at IS NULL"
        )
    )
    op.alter_column(
        "quiz_sessions",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    op.alter_column("quiz_sessions", "correct_count", existing_type=sa.Integer(), nullable=True)
    op.alter_column("quiz_sessions", "wrong_count", existing_type=sa.Integer(), nullable=True)
    op.alter_column("quiz_sessions", "accuracy", existing_type=sa.Numeric(5, 4), nullable=True)
    op.alter_column("quiz_sessions", "exp_gained", existing_type=sa.Integer(), nullable=True)
    op.alter_column("quiz_sessions", "points_gained", existing_type=sa.Integer(), nullable=True)
    op.alter_column("quiz_sessions", "report_json", existing_type=sa.JSON(), nullable=True)
    op.alter_column("quiz_sessions", "finished_at", existing_type=sa.DateTime(), nullable=True)

    op.alter_column("quiz_sessions", "status", server_default=None)
    op.alter_column("quiz_sessions", "current_index", server_default=None)


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE quiz_sessions SET "
            "correct_count = COALESCE(correct_count, 0), "
            "wrong_count = COALESCE(wrong_count, 0), "
            "accuracy = COALESCE(accuracy, 0), "
            "exp_gained = COALESCE(exp_gained, 0), "
            "points_gained = COALESCE(points_gained, 0), "
            "report_json = COALESCE(report_json, JSON_OBJECT()), "
            "finished_at = COALESCE(finished_at, updated_at, created_at) "
            "WHERE status = 'in_progress' OR finished_at IS NULL "
            "OR correct_count IS NULL OR report_json IS NULL"
        )
    )
    op.execute(sa.text("DELETE FROM quiz_sessions WHERE status = 'in_progress'"))

    op.alter_column("quiz_sessions", "finished_at", existing_type=sa.DateTime(), nullable=False)
    op.alter_column("quiz_sessions", "report_json", existing_type=sa.JSON(), nullable=False)
    op.alter_column("quiz_sessions", "points_gained", existing_type=sa.Integer(), nullable=False)
    op.alter_column("quiz_sessions", "exp_gained", existing_type=sa.Integer(), nullable=False)
    op.alter_column("quiz_sessions", "accuracy", existing_type=sa.Numeric(5, 4), nullable=False)
    op.alter_column("quiz_sessions", "wrong_count", existing_type=sa.Integer(), nullable=False)
    op.alter_column("quiz_sessions", "correct_count", existing_type=sa.Integer(), nullable=False)

    op.drop_constraint("fk_quiz_sessions_knowledge_base_id", "quiz_sessions", type_="foreignkey")
    op.drop_index("ix_quiz_sessions_knowledge_base_id", table_name="quiz_sessions")
    op.drop_index("ix_quiz_sessions_status", table_name="quiz_sessions")
    op.drop_column("quiz_sessions", "updated_at")
    op.drop_column("quiz_sessions", "knowledge_base_id")
    op.drop_column("quiz_sessions", "current_index")
    op.drop_column("quiz_sessions", "status")
