"""add missing RLS write policies for chat messages, citations, threads

Revision ID: 746bdb2c5339
Revises: ff9e028be0d8
Create Date: 2026-08-03 12:32:37.835969

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '746bdb2c5339'
down_revision: Union[str, Sequence[str], None] = 'ff9e028be0d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    The initial schema migration enabled RLS on chat_threads/chat_messages/
    message_citations but only ever added SELECT (and chat_threads INSERT)
    policies. With RLS enabled and no matching policy, Postgres denies by
    default, so every write the app actually performs after that first
    insert — appending a grounded turn's messages/citations, and bumping or
    deleting a thread — was silently rejected. Add the missing write
    policies, following the existing ownership-check pattern.
    """
    op.execute("""
        CREATE POLICY chat_messages_insert_own ON chat_messages
        FOR INSERT TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM chat_threads
                WHERE chat_threads.id = thread_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)

    op.execute("""
        CREATE POLICY message_citations_insert_own ON message_citations
        FOR INSERT TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM chat_messages
                JOIN chat_threads ON chat_threads.id = chat_messages.thread_id
                WHERE chat_messages.id = message_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)

    op.execute("""
        CREATE POLICY chat_threads_update_own ON chat_threads
        FOR UPDATE TO authenticated
        USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id)
    """)

    op.execute("""
        CREATE POLICY chat_threads_delete_own ON chat_threads
        FOR DELETE TO authenticated
        USING (auth.uid() = user_id)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY chat_threads_delete_own ON chat_threads")
    op.execute("DROP POLICY chat_threads_update_own ON chat_threads")
    op.execute("DROP POLICY message_citations_insert_own ON message_citations")
    op.execute("DROP POLICY chat_messages_insert_own ON chat_messages")
