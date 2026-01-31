"""Add chapter versions and version management

Revision ID: 003
Revises: 002
Create Date: 2026-01-29 00:00:00.000000

添加章节版本管理系统：
- 创建 chapter_versions 表用于存储章节历史版本
- 扩展 task_results 表添加版本管理字段：
  - current_version_id: 当前版本ID
  - version_count: 版本总数
  - rewrite_status: 重写状态
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加章节版本管理功能"""

    # 1. 创建 chapter_versions 表
    op.create_table(
        'chapter_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('chapter_index', sa.Integer(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('consistency_score', sa.Float(), nullable=True),
        sa.Column('evaluation', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('rewrite_reason', sa.Text(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. 创建索引
    op.create_index('ix_chapter_versions_session_id', 'chapter_versions', ['session_id'])
    op.create_index('ix_chapter_versions_task_id', 'chapter_versions', ['task_id'])
    op.create_index('ix_chapter_versions_chapter_index', 'chapter_versions', ['chapter_index'])
    op.create_index(
        'ix_chapter_versions_session_chapter_version',
        'chapter_versions',
        ['session_id', 'chapter_index', 'version_number']
    )

    # 3. 扩展 task_results 表，添加版本管理字段
    op.add_column(
        'task_results',
        sa.Column('current_version_id', sa.String(), nullable=True)
    )
    op.add_column(
        'task_results',
        sa.Column('version_count', sa.Integer(), nullable=False, server_default='1')
    )
    op.add_column(
        'task_results',
        sa.Column('rewrite_status', sa.String(), nullable=False, server_default='none')
    )


def downgrade() -> None:
    """移除章节版本管理功能"""

    # 1. 移除 task_results 扩展字段
    op.drop_column('task_results', 'rewrite_status')
    op.drop_column('task_results', 'version_count')
    op.drop_column('task_results', 'current_version_id')

    # 2. 删除索引
    op.drop_index('ix_chapter_versions_session_chapter_version', table_name='chapter_versions')
    op.drop_index('ix_chapter_versions_chapter_index', table_name='chapter_versions')
    op.drop_index('ix_chapter_versions_task_id', table_name='chapter_versions')
    op.drop_index('ix_chapter_versions_session_id', table_name='chapter_versions')

    # 3. 删除 chapter_versions 表
    op.drop_table('chapter_versions')
