"""add users.token_version

Revision ID: b4e8d2f6a1c3
Revises: a7c2e5d1b9f0
Create Date: 2026-11-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b4e8d2f6a1c3'
down_revision: Union[str, Sequence[str], None] = 'a7c2e5d1b9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'token_version')
