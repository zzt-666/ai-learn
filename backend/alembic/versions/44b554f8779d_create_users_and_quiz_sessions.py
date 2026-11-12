"""create users and quiz_sessions

Revision ID: 44b554f8779d
Revises:
Create Date: 2026-11-11 15:05:05.449722

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "44b554f8779d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("openid", sa.String(length=64), nullable=False),
        sa.Column("unionid", sa.String(length=64), nullable=True),
        sa.Column("nickname", sa.String(length=32), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("exp", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("openid"),
    )
    op.create_index(op.f("ix_users_openid"), "users", ["openid"], unique=False)

    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_name", sa.String(length=64), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("exp_gained", sa.Integer(), nullable=False),
        sa.Column("points_gained", sa.Integer(), nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("source_session_id", sa.BigInteger(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_sessions_user_id"), "quiz_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_sessions_user_id"), table_name="quiz_sessions")
    op.drop_table("quiz_sessions")
    op.drop_index(op.f("ix_users_openid"), table_name="users")
    op.drop_table("users")
