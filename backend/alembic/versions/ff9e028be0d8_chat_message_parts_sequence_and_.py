"""chat message parts, sequence, and citation metadata

Revision ID: ff9e028be0d8
Revises: cfe6a2139bf2
Create Date: 2026-08-03 00:03:04.336070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ff9e028be0d8'
down_revision: Union[str, Sequence[str], None] = 'cfe6a2139bf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_messages', sa.Column('parts', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column('chat_messages', sa.Column('sequence', sa.Integer(), nullable=False))
    op.alter_column('chat_messages', 'content',
               existing_type=sa.TEXT(),
               nullable=True)
    op.create_unique_constraint('uq_chat_messages_thread_sequence', 'chat_messages', ['thread_id', 'sequence'])

    op.add_column('message_citations', sa.Column('citation_index', sa.Integer(), nullable=False))
    op.add_column('message_citations', sa.Column('excerpt', sa.Text(), nullable=False))
    op.add_column('message_citations', sa.Column('ticker', sa.String(length=16), nullable=False))
    op.add_column('message_citations', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('message_citations', sa.Column('form', sa.String(length=16), nullable=False))
    op.add_column('message_citations', sa.Column('filing_date', sa.Date(), nullable=False))
    op.add_column('message_citations', sa.Column('page', sa.String(length=64), nullable=True))
    op.add_column('message_citations', sa.Column('section', sa.Text(), nullable=True))
    op.create_unique_constraint('uq_message_citations_message_index', 'message_citations', ['message_id', 'citation_index'])
    op.drop_column('message_citations', 'updated_at')
    op.drop_column('message_citations', 'quote')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('message_citations', sa.Column('quote', sa.TEXT(), autoincrement=False, nullable=False))
    op.add_column('message_citations', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.drop_constraint('uq_message_citations_message_index', 'message_citations', type_='unique')
    op.drop_column('message_citations', 'section')
    op.drop_column('message_citations', 'page')
    op.drop_column('message_citations', 'filing_date')
    op.drop_column('message_citations', 'form')
    op.drop_column('message_citations', 'company_name')
    op.drop_column('message_citations', 'ticker')
    op.drop_column('message_citations', 'excerpt')
    op.drop_column('message_citations', 'citation_index')

    op.drop_constraint('uq_chat_messages_thread_sequence', 'chat_messages', type_='unique')
    op.alter_column('chat_messages', 'content',
               existing_type=sa.TEXT(),
               nullable=False)
    op.drop_column('chat_messages', 'sequence')
    op.drop_column('chat_messages', 'parts')
