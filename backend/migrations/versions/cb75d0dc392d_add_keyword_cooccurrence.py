"""add keyword_cooccurrence

Revision ID: cb75d0dc392d
Revises: cbb1e5e7cb84
Create Date: 2026-08-30 01:14:18.981094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb75d0dc392d'
down_revision: Union[str, Sequence[str], None] = 'cbb1e5e7cb84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'keyword_cooccurrence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_a_id', sa.Integer(), nullable=True),
        sa.Column('keyword_b_id', sa.Integer(), nullable=True),
        sa.Column('co_count', sa.Integer(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['keyword_a_id'], ['keywords.id'], name='fk_kwcooc_a'),
        sa.ForeignKeyConstraint(['keyword_b_id'], ['keywords.id'], name='fk_kwcooc_b'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_keyword_cooccurrence_id', 'keyword_cooccurrence', ['id'])
    op.create_index('ix_keyword_cooccurrence_keyword_a_id', 'keyword_cooccurrence', ['keyword_a_id'])
    op.create_index('ix_keyword_cooccurrence_keyword_b_id', 'keyword_cooccurrence', ['keyword_b_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_keyword_cooccurrence_keyword_b_id', table_name='keyword_cooccurrence')
    op.drop_index('ix_keyword_cooccurrence_keyword_a_id', table_name='keyword_cooccurrence')
    op.drop_index('ix_keyword_cooccurrence_id', table_name='keyword_cooccurrence')
    op.drop_table('keyword_cooccurrence')
