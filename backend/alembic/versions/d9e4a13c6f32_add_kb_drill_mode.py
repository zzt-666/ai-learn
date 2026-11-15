"""add kb drill mode and question tables

Revision ID: d9e4a13c6f32
Revises: c8d3f02b5e21
Create Date: 2026-11-14 22:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9e4a13c6f32"
down_revision: Union[str, Sequence[str], None] = "c8d3f02b5e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("mode", sa.String(length=16), nullable=True))
    op.add_column("knowledge_bases", sa.Column("suggested_mode", sa.String(length=16), nullable=True))
    op.add_column("knowledge_bases", sa.Column("mode_confirmed_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_knowledge_bases_mode"), "knowledge_bases", ["mode"], unique=False)

    op.create_table(
        "kb_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("qtype", sa.String(length=16), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("answer_indices_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("explanation_source", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kb_questions_knowledge_base_id"), "kb_questions", ["knowledge_base_id"], unique=False)
    op.create_index(op.f("ix_kb_questions_document_id"), "kb_questions", ["document_id"], unique=False)

    op.create_table(
        "kb_question_practice",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["kb_questions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_kb_practice_user_question"),
    )
    op.create_index(op.f("ix_kb_question_practice_user_id"), "kb_question_practice", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_kb_question_practice_knowledge_base_id"),
        "kb_question_practice",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kb_question_practice_question_id"),
        "kb_question_practice",
        ["question_id"],
        unique=False,
    )

    op.add_column(
        "quiz_generation_tasks",
        sa.Column("drill_round", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_generation_tasks", "drill_round")
    op.drop_index(op.f("ix_kb_question_practice_question_id"), table_name="kb_question_practice")
    op.drop_index(op.f("ix_kb_question_practice_knowledge_base_id"), table_name="kb_question_practice")
    op.drop_index(op.f("ix_kb_question_practice_user_id"), table_name="kb_question_practice")
    op.drop_table("kb_question_practice")
    op.drop_index(op.f("ix_kb_questions_document_id"), table_name="kb_questions")
    op.drop_index(op.f("ix_kb_questions_knowledge_base_id"), table_name="kb_questions")
    op.drop_table("kb_questions")
    op.drop_index(op.f("ix_knowledge_bases_mode"), table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "mode_confirmed_at")
    op.drop_column("knowledge_bases", "suggested_mode")
    op.drop_column("knowledge_bases", "mode")
