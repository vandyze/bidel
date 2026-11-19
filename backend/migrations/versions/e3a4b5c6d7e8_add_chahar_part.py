"""add part to chahar onsor

Revision ID: e3a4b5c6d7e8
Revises: d1f2a3b4c5d6
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'd1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('chahar_onsor')}
    if 'part' not in columns:
        op.add_column('chahar_onsor', sa.Column('part', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('chahar_onsor')}
    if 'part' in columns:
        with op.batch_alter_table('chahar_onsor') as batch:
            batch.drop_column('part')
