"""add chahar onsor

Revision ID: c9d4e7f1a2b6
Revises: b4e8d2f6a1c3
Create Date: 2026-11-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d4e7f1a2b6'
down_revision: Union[str, Sequence[str], None] = 'b4e8d2f6a1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'chahar_onsor' not in tables:
        op.create_table(
            'chahar_onsor',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('number', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
        )

    indexes = {i['name'] for i in sa.inspect(bind).get_indexes('chahar_onsor')}
    if 'ix_chahar_onsor_number' not in indexes:
        op.create_index('ix_chahar_onsor_number', 'chahar_onsor', ['number'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'chahar_onsor' in inspector.get_table_names():
        indexes = {i['name'] for i in inspector.get_indexes('chahar_onsor')}
        if 'ix_chahar_onsor_number' in indexes:
            op.drop_index('ix_chahar_onsor_number', table_name='chahar_onsor')
        op.drop_table('chahar_onsor')
