from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0002_tokens_and_apikey_ref'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('profile', sa.String(length=120), nullable=True, unique=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_on', sa.BigInteger(), nullable=True),
        sa.Column('expires_in', sa.Integer(), nullable=True),
        sa.Column('token_type', sa.String(length=40), nullable=True),
        sa.Column('scope', sa.Text(), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('client_id', sa.String(length=64), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.add_column('api_keys', sa.Column('token_id', sa.Integer(), nullable=True))
    # SQLite 호환: batch_alter_table 사용
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.create_foreign_key('fk_api_keys_token_id', 'tokens', ['token_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.drop_constraint('fk_api_keys_token_id', type_='foreignkey')
        batch_op.drop_column('token_id')
    op.drop_table('tokens')

