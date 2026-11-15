"""add master chapter map tables and status fields

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-11-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "e1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("master_map_status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("master_map_error", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("master_point_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        op.f("ix_knowledge_bases_master_map_status"),
        "knowledge_bases",
        ["master_map_status"],
        unique=False,
    )

    op.create_table(
        "kb_master_sections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_span", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_kb_master_sections_knowledge_base_id"),
        "kb_master_sections",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kb_master_sections_document_id"),
        "kb_master_sections",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "kb_master_points",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("section_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["kb_master_sections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_kb_master_points_section_id"),
        "kb_master_points",
        ["section_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kb_master_points_knowledge_base_id"),
        "kb_master_points",
        ["knowledge_base_id"],
        unique=False,
    )

    op.create_table(
        "kb_master_point_coverage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("point_id", sa.BigInteger(), nullable=False),
        sa.Column("seen_count", sa.Integer(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["point_id"], ["kb_master_points.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "point_id", name="uq_kb_master_coverage_user_point"),
    )
    op.create_index(
        op.f("ix_kb_master_point_coverage_user_id"),
        "kb_master_point_coverage",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kb_master_point_coverage_knowledge_base_id"),
        "kb_master_point_coverage",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_kb_master_point_coverage_point_id"),
        "kb_master_point_coverage",
        ["point_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_kb_master_point_coverage_point_id"),
        table_name="kb_master_point_coverage",
    )
    op.drop_index(
        op.f("ix_kb_master_point_coverage_knowledge_base_id"),
        table_name="kb_master_point_coverage",
    )
    op.drop_index(
        op.f("ix_kb_master_point_coverage_user_id"),
        table_name="kb_master_point_coverage",
    )
    op.drop_table("kb_master_point_coverage")
    op.drop_index(op.f("ix_kb_master_points_knowledge_base_id"), table_name="kb_master_points")
    op.drop_index(op.f("ix_kb_master_points_section_id"), table_name="kb_master_points")
    op.drop_table("kb_master_points")
    op.drop_index(op.f("ix_kb_master_sections_document_id"), table_name="kb_master_sections")
    op.drop_index(
        op.f("ix_kb_master_sections_knowledge_base_id"),
        table_name="kb_master_sections",
    )
    op.drop_table("kb_master_sections")
    op.drop_index(op.f("ix_knowledge_bases_master_map_status"), table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "master_point_count")
    op.drop_column("knowledge_bases", "master_map_error")
    op.drop_column("knowledge_bases", "master_map_status")
