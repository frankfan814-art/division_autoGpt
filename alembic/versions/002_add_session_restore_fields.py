"""Add session restore fields

Revision ID: 002
Revises: 001
Create Date: 2025-01-25 00:00:00.000000

添加会话恢复相关字段到 sessions 表：
- engine_state: 存储引擎状态信息
- current_task_index: 当前任务索引
- is_resumable: 是否可以恢复
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加会话恢复字段"""

    # 添加 engine_state 列
    op.add_column(
        'sessions',
        sa.Column('engine_state', sa.JSON(), nullable=True)
    )

    # 添加 current_task_index 列
    op.add_column(
        'sessions',
        sa.Column('current_task_index', sa.Integer(), nullable=True)
    )

    # 添加 is_resumable 列，默认值为 True
    op.add_column(
        'sessions',
        sa.Column('is_resumable', sa.Boolean(), nullable=False, server_default='1')
    )


def downgrade() -> None:
    """移除会话恢复字段"""

    op.drop_column('sessions', 'is_resumable')
    op.drop_column('sessions', 'current_task_index')
    op.drop_column('sessions', 'engine_state')
