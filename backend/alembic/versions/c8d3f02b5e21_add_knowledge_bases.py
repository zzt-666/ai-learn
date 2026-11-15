"""add knowledge bases and documents

Revision ID: c8d3f02b5e21
Revises: b7c2e91a4f10
Create Date: 2026-11-14 15:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d3f02b5e21"
down_revision: Union[str, Sequence[str], None] = "b7c2e91a4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_bases_user_id"), "knowledge_bases", ["user_id"], unique=False)
    op.create_index(op.f("ix_knowledge_bases_updated_at"), "knowledge_bases", ["updated_at"], unique=False)

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_documents_knowledge_base_id"),
        "knowledge_documents",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(op.f("ix_knowledge_documents_user_id"), "knowledge_documents", ["user_id"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_status"), "knowledge_documents", ["status"], unique=False)

    op.add_column(
        "quiz_generation_tasks",
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        op.f("ix_quiz_generation_tasks_knowledge_base_id"),
        "quiz_generation_tasks",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_quiz_generation_tasks_knowledge_base_id",
        "quiz_generation_tasks",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_quiz_generation_tasks_knowledge_base_id",
        "quiz_generation_tasks",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_quiz_generation_tasks_knowledge_base_id"),
        table_name="quiz_generation_tasks",
    )
    op.drop_column("quiz_generation_tasks", "knowledge_base_id")

    op.drop_index(op.f("ix_knowledge_documents_status"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_user_id"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_knowledge_base_id"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_index(op.f("ix_knowledge_bases_updated_at"), table_name="knowledge_bases")
    op.drop_index(op.f("ix_knowledge_bases_user_id"), table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
