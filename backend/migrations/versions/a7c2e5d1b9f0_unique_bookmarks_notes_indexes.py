"""unique bookmarks/notes + performance indexes

Revision ID: a7c2e5d1b9f0
Revises: f3a1c9e7b2d4
Create Date: 2026-11-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a7c2e5d1b9f0'
down_revision: Union[str, Sequence[str], None] = 'f3a1c9e7b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _dedupe(table: str) -> None:
    # از هر گروه تکراری، قدیمی‌ترین ردیف می‌ماند
    op.execute(f"""
        DELETE FROM {table} WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, poem_type, poem_id, COALESCE(couplet_index, -1)
                    ORDER BY id) AS rn
                FROM {table}
            ) t WHERE t.rn > 1
        )
    """)


def upgrade() -> None:
    _dedupe('bookmarks')
    _dedupe('notes')
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_bookmarks_user_poem ON bookmarks "
               "(user_id, poem_type, poem_id, COALESCE(couplet_index, -1))")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_notes_user_poem ON notes "
               "(user_id, poem_type, poem_id, COALESCE(couplet_index, -1))")
    for name, table, col in [
        ('ix_ghazal_keywords_ghazal_id', 'ghazal_keywords', 'ghazal_id'),
        ('ix_ghazal_keywords_keyword_id', 'ghazal_keywords', 'keyword_id'),
        ('ix_terjee_keywords_terjee_id', 'terjee_keywords', 'terjee_id'),
        ('ix_terjee_keywords_keyword_id', 'terjee_keywords', 'keyword_id'),
        ('ix_bookmarks_user_id', 'bookmarks', 'user_id'),
        ('ix_notes_user_id', 'notes', 'user_id'),
    ]:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")


def downgrade() -> None:
    for name in ['ix_notes_user_id', 'ix_bookmarks_user_id', 'ix_terjee_keywords_keyword_id',
                 'ix_terjee_keywords_terjee_id', 'ix_ghazal_keywords_keyword_id',
                 'ix_ghazal_keywords_ghazal_id', 'uq_notes_user_poem', 'uq_bookmarks_user_poem']:
        op.execute(f"DROP INDEX IF EXISTS {name}")
