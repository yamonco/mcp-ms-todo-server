from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0006_drop_tokens_raw'
down_revision = '0005_api_key_tools'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('tokens') as batch_op:
        try:
            batch_op.drop_column('raw')
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table('tokens') as batch_op:
        batch_op.add_column(sa.Column('raw', sa.JSON(), nullable=True))

