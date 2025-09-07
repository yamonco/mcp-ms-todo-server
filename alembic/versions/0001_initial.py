from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('name', sa.String(length=100), primary_key=True),
        sa.Column('tools', sa.JSON(), nullable=True),
    )
    op.create_table(
        'api_keys',
        sa.Column('key', sa.String(length=200), primary_key=True),
        sa.Column('template', sa.String(length=32), nullable=True),
        sa.Column('allowed_tools', sa.JSON(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(length=120), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('token_file', sa.String(length=400), nullable=True),
        sa.Column('token_profile', sa.String(length=120), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('api_keys')
    op.drop_table('roles')

