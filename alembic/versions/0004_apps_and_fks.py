from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '0004_apps_and_fks'
down_revision = '0003_drop_token_file_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'apps',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('profile', sa.String(length=120), nullable=True, unique=True),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('client_id', sa.String(length=64), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.add_column(sa.Column('app_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_api_keys_app_id', 'apps', ['app_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.drop_constraint('fk_api_keys_app_id', type_='foreignkey')
        batch_op.drop_column('app_id')
    op.drop_table('apps')

