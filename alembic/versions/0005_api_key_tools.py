from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0005_api_key_tools'
down_revision = '0004_apps_and_fks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_key_tools',
        sa.Column('key', sa.String(length=200), sa.ForeignKey('api_keys.key'), primary_key=True),
        sa.Column('tool', sa.String(length=200), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table('api_key_tools')

