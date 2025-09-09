from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0009_app_subscription_id'
down_revision = '0008_casbin_rule'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('apps') as batch_op:
        batch_op.add_column(sa.Column('subscription_id', sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('apps') as batch_op:
        batch_op.drop_column('subscription_id')

