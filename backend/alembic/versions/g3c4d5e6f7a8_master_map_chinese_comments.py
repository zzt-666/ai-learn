"""add Chinese COMMENT on master map tables/columns

Revision ID: g3c4d5e6f7a8
Revises: f2b3c4d5e6f7
Create Date: 2026-11-15
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "g3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # knowledge_bases 扩展字段
    op.execute(
        "ALTER TABLE knowledge_bases "
        "MODIFY COLUMN master_map_status VARCHAR(16) NULL "
        "COMMENT '学透要点地图状态：pending生成中/ready就绪/failed失败'"
    )
    op.execute(
        "ALTER TABLE knowledge_bases "
        "MODIFY COLUMN master_map_error VARCHAR(512) NULL "
        "COMMENT '学透要点地图失败原因（可读文案）'"
    )
    op.execute(
        "ALTER TABLE knowledge_bases "
        "MODIFY COLUMN master_point_count INT NOT NULL DEFAULT 0 "
        "COMMENT '学透要点总数（冗余计数，详情展示用）'"
    )

    # 章节表
    op.execute("ALTER TABLE kb_master_sections COMMENT='学透章节/节节点'")
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN knowledge_base_id BIGINT NOT NULL COMMENT '所属知识库ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN document_id BIGINT NOT NULL COMMENT '来源文档ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN ordinal INT NOT NULL COMMENT '章节顺序（从0起）'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN title VARCHAR(256) NOT NULL COMMENT '章节标题'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN summary TEXT NULL COMMENT '章节短摘要（可空）'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN source_span VARCHAR(64) NULL COMMENT '原文起止提示（可选）'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'"
    )
    op.execute(
        "ALTER TABLE kb_master_sections "
        "MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
        "ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'"
    )

    # 要点表
    op.execute("ALTER TABLE kb_master_points COMMENT='学透要点/考点'")
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN section_id BIGINT NOT NULL COMMENT '所属章节ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN knowledge_base_id BIGINT NOT NULL COMMENT '所属知识库ID（冗余便于按库查）'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN ordinal INT NOT NULL COMMENT '节内顺序'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN title VARCHAR(256) NOT NULL COMMENT '考点短标题'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN summary TEXT NOT NULL COMMENT '要点说明（出题主依据）'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN keywords_json JSON NULL COMMENT '可选关键词JSON数组'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN is_active INT NOT NULL COMMENT '是否有效：1有效/0替换后失效'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'"
    )
    op.execute(
        "ALTER TABLE kb_master_points "
        "MODIFY COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
        "ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'"
    )

    # 覆盖表
    op.execute("ALTER TABLE kb_master_point_coverage COMMENT='用户学透要点覆盖进度（对称刷题练习表）'")
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN user_id BIGINT NOT NULL COMMENT '用户ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN knowledge_base_id BIGINT NOT NULL COMMENT '知识库ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN point_id BIGINT NOT NULL COMMENT '要点ID'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN seen_count INT NOT NULL COMMENT '进入含该点之局的次数'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN last_seen_at DATETIME NOT NULL COMMENT '最近一次开局见到该点的时间'"
    )
    op.execute(
        "ALTER TABLE kb_master_point_coverage "
        "MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'"
    )


def downgrade() -> None:
    # Comments are documentation-only; leave columns intact on downgrade.
    pass
