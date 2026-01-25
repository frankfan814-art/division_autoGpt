"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables"""

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False, server_default='novel'),
        sa.Column('status', sa.String(), nullable=False, server_default='created'),
        sa.Column('goal', sa.JSON(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llm_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)
    op.create_index(op.f('ix_sessions_status'), 'sessions', ['status'], unique=False)
    op.create_index(op.f('ix_sessions_created_at'), 'sessions', ['created_at'], unique=False)

    # Create task_results table
    op.create_table(
        'task_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('task_metadata', sa.JSON(), nullable=True),
        sa.Column('evaluation', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('chapter_index', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_results_session_id'), 'task_results', ['session_id'], unique=False)
    op.create_index(op.f('ix_task_results_task_id'), 'task_results', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_results_task_type'), 'task_results', ['task_type'], unique=False)
    op.create_index(op.f('ix_task_results_chapter_index'), 'task_results', ['chapter_index'], unique=False)


def downgrade() -> None:
    """Drop initial tables"""

    op.drop_index(op.f('ix_task_results_chapter_index'), table_name='task_results')
    op.drop_index(op.f('ix_task_results_task_type'), table_name='task_results')
    op.drop_index(op.f('ix_task_results_task_id'), table_name='task_results')
    op.drop_index(op.f('ix_task_results_session_id'), table_name='task_results')
    op.drop_table('task_results')

    op.drop_index(op.f('ix_sessions_created_at'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_status'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')
