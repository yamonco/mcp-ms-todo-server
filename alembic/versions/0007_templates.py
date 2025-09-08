from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0007_templates'
down_revision = '0006_drop_tokens_raw'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'templates',
        sa.Column('name', sa.String(length=100), primary_key=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'template_tools',
        sa.Column('template', sa.String(length=100), sa.ForeignKey('templates.name'), primary_key=True),
        sa.Column('tool', sa.String(length=200), primary_key=True),
    )
    op.create_table(
        'template_apps',
        sa.Column('template', sa.String(length=100), sa.ForeignKey('templates.name'), primary_key=True),
        sa.Column('app_id', sa.Integer(), sa.ForeignKey('apps.id'), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('template_apps')
    op.drop_table('template_tools')
    op.drop_table('templates')

