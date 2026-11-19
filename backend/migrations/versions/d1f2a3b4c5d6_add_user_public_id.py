"""add random public id to users

Revision ID: d1f2a3b4c5d6
Revises: c9d4e7f1a2b6
Create Date: 2026-11-20 00:00:00.000000

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c9d4e7f1a2b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'public_id' not in columns:
        op.add_column('users', sa.Column('public_id', sa.String(), nullable=True))

    # شناسهٔ تصادفی برای کاربران موجود
    rows = bind.execute(sa.text("SELECT id FROM users WHERE public_id IS NULL")).fetchall()
    for (user_id,) in rows:
        bind.execute(
            sa.text("UPDATE users SET public_id = :pid WHERE id = :uid"),
            {"pid": "u" + secrets.token_hex(8), "uid": user_id},
        )

    indexes = {i['name'] for i in sa.inspect(bind).get_indexes('users')}
    if 'ix_users_public_id' not in indexes:
        op.create_index('ix_users_public_id', 'users', ['public_id'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = {i['name'] for i in inspector.get_indexes('users')}
    if 'ix_users_public_id' in indexes:
        op.drop_index('ix_users_public_id', table_name='users')

    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'public_id' in columns:
        with op.batch_alter_table('users') as batch:
            batch.drop_column('public_id')
