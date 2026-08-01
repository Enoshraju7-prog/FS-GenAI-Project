"""initial schema

Revision ID: 186443db98ec
Revises:
Create Date: 2026-08-01 20:54:39.152306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '186443db98ec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_threads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('source_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('ticker', sa.String(length=16), nullable=False),
    sa.Column('cik', sa.String(length=10), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=True),
    sa.Column('form', sa.String(length=16), nullable=False),
    sa.Column('filing_date', sa.Date(), nullable=False),
    sa.Column('report_date', sa.Date(), nullable=True),
    sa.Column('fiscal_year', sa.Integer(), nullable=True),
    sa.Column('accession_number', sa.String(length=25), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('accession_number', name='uq_source_documents_accession_number')
    )
    op.create_index('ix_source_documents_ticker_fiscal_year', 'source_documents', ['ticker', 'fiscal_year'], unique=False)
    op.create_table('chat_messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('thread_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.Enum('user', 'assistant', name='messagerole'), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('document_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', content)", persisted=True), nullable=True),
    sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['source_documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
    """)
    op.execute("""
        CREATE INDEX ix_document_chunks_search_vector_gin
        ON document_chunks
        USING gin (search_vector)
    """)
    op.execute("""
        CREATE INDEX ix_document_chunks_chunk_metadata_gin
        ON document_chunks
        USING gin (chunk_metadata)
    """)
    op.create_table('message_citations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('message_id', sa.UUID(), nullable=False),
    sa.Column('chunk_id', sa.UUID(), nullable=False),
    sa.Column('quote', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    _enable_rls_and_policies()


def _enable_rls_and_policies() -> None:
    for table in ["users", "source_documents", "document_chunks", "chat_threads", "chat_messages", "message_citations"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # users — read and update own row only
    op.execute("""
        CREATE POLICY users_select_own ON users
        FOR SELECT TO authenticated
        USING (auth.uid() = id)
    """)
    op.execute("""
        CREATE POLICY users_update_own ON users
        FOR UPDATE TO authenticated
        USING (auth.uid() = id)
        WITH CHECK (auth.uid() = id)
    """)

    # source_documents — any authenticated user can read
    op.execute("""
        CREATE POLICY source_documents_select_authenticated ON source_documents
        FOR SELECT TO authenticated
        USING (true)
    """)

    # document_chunks — any authenticated user can read
    op.execute("""
        CREATE POLICY document_chunks_select_authenticated ON document_chunks
        FOR SELECT TO authenticated
        USING (true)
    """)

    # chat_threads — own rows only
    op.execute("""
        CREATE POLICY chat_threads_select_own ON chat_threads
        FOR SELECT TO authenticated
        USING (auth.uid() = user_id)
    """)
    op.execute("""
        CREATE POLICY chat_threads_insert_own ON chat_threads
        FOR INSERT TO authenticated
        WITH CHECK (auth.uid() = user_id)
    """)

    # chat_messages — readable through owned threads
    op.execute("""
        CREATE POLICY chat_messages_select_own ON chat_messages
        FOR SELECT TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM chat_threads
                WHERE chat_threads.id = thread_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)

    # message_citations — any authenticated user can read
    op.execute("""
        CREATE POLICY message_citations_select_authenticated ON message_citations
        FOR SELECT TO authenticated
        USING (true)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('message_citations')
    op.drop_table('document_chunks')
    op.drop_table('chat_messages')
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.drop_index('ix_source_documents_ticker_fiscal_year', table_name='source_documents')
    op.drop_table('source_documents')
    op.drop_table('chat_threads')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS vector")
