"""add quiz_generation_tasks

Revision ID: b7c2e91a4f10
Revises: 44b554f8779d
Create Date: 2026-11-13 21:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e91a4f10"
down_revision: Union[str, Sequence[str], None] = "44b554f8779d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_generation_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("topic_name_input", sa.String(length=64), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quiz_generation_tasks_user_id"),
        "quiz_generation_tasks",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quiz_generation_tasks_status"),
        "quiz_generation_tasks",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_generation_tasks_status"), table_name="quiz_generation_tasks")
    op.drop_index(op.f("ix_quiz_generation_tasks_user_id"), table_name="quiz_generation_tasks")
    op.drop_table("quiz_generation_tasks")
