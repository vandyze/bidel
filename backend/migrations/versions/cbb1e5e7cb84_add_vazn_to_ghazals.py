"""add vazn to ghazals

Revision ID: cbb1e5e7cb84
Revises: d754fa0f6ccb
Create Date: 2026-08-15 00:00:00.000000

"""
import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbb1e5e7cb84'
down_revision: Union[str, Sequence[str], None] = 'd754fa0f6ccb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VAZN_PATH = Path(__file__).resolve().parents[2] / "data" / "ganjoor_vazn.json"


def upgrade() -> None:
    op.add_column('ghazals', sa.Column('vazn', sa.String(), nullable=True))

    if not VAZN_PATH.exists():
        return
    with open(VAZN_PATH, encoding="utf-8") as f:
        vazn_data = json.load(f)

    conn = op.get_bind()
    ghazals_table = sa.table(
        'ghazals',
        sa.column('number', sa.Integer),
        sa.column('vazn', sa.String),
    )
    for num, entry in vazn_data.items():
        arkan = entry.get("arkan")
        if not arkan:
            continue
        conn.execute(
            ghazals_table.update()
            .where(ghazals_table.c.number == int(num))
            .values(vazn=arkan)
        )


def downgrade() -> None:
    op.drop_column('ghazals', 'vazn')
