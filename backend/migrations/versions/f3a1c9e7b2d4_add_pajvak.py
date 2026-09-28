"""add pajvak

Revision ID: f3a1c9e7b2d4
Revises: cb75d0dc392d
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a1c9e7b2d4'
down_revision: Union[str, Sequence[str], None] = 'cb75d0dc392d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pajvaks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('ref_type', sa.String(), nullable=False),
        sa.Column('ref_ghazal_number', sa.Integer(), nullable=True),
        sa.Column('ref_beit_index', sa.Integer(), nullable=True),
        sa.Column('ref_terjee_number', sa.Integer(), nullable=True),
        sa.Column('cover_filename', sa.String(), nullable=True),
        sa.Column('audio_filename', sa.String(), nullable=True),
        sa.Column('audio_duration', sa.Integer(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('poem', sa.JSON(), nullable=True),
        sa.Column('narrative', sa.JSON(), nullable=True),
        sa.Column('credits', sa.JSON(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_pajvaks_slug', 'pajvaks', ['slug'], unique=True)
    op.create_index('ix_pajvaks_ref_ghazal_number', 'pajvaks', ['ref_ghazal_number'])
    op.create_index('ix_pajvaks_ref_terjee_number', 'pajvaks', ['ref_terjee_number'])


def downgrade() -> None:
    op.drop_index('ix_pajvaks_ref_terjee_number', table_name='pajvaks')
    op.drop_index('ix_pajvaks_ref_ghazal_number', table_name='pajvaks')
    op.drop_index('ix_pajvaks_slug', table_name='pajvaks')
    op.drop_table('pajvaks')
