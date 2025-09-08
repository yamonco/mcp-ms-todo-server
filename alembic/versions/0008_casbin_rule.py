from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0008_casbin_rule'
down_revision = '0007_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'casbin_rule',
        sa.Column('ptype', sa.String(length=100), primary_key=True),
        sa.Column('v0', sa.String(length=256), primary_key=True, nullable=True),
        sa.Column('v1', sa.String(length=256), primary_key=True, nullable=True),
        sa.Column('v2', sa.String(length=256), primary_key=True, nullable=True),
        sa.Column('v3', sa.String(length=256), primary_key=True, nullable=True),
        sa.Column('v4', sa.String(length=256), primary_key=True, nullable=True),
        sa.Column('v5', sa.String(length=256), primary_key=True, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('casbin_rule')

