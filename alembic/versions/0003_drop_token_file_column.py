from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0003_drop_token_file_column'
down_revision = '0002_tokens_and_apikey_ref'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('api_keys') as batch_op:
        try:
            batch_op.drop_column('token_file')
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.add_column(sa.Column('token_file', sa.String(length=400), nullable=True))

