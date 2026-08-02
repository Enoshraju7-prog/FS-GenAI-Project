"""chunk and table extraction schema

Revision ID: cfe6a2139bf2
Revises: b7baf07266dd
Create Date: 2026-08-02 22:40:58.965414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cfe6a2139bf2'
down_revision: Union[str, Sequence[str], None] = 'b7baf07266dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_tables',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('table_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('units', sa.String(length=255), nullable=True),
        sa.Column('markdown', sa.Text(), nullable=False),
        sa.Column('table_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('source_html_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['source_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'table_index', name='uq_document_tables_document_table'),
    )
    op.create_index('ix_document_tables_document_id', 'document_tables', ['document_id'], unique=False)

    # search_vector is GENERATED ALWAYS AS (...) STORED, computed from `content` — Postgres
    # refuses to drop `content` while a generated column depends on it, so drop the generated
    # column (and its index) first, rebuild it against `text` after the rename below.
    op.drop_index('ix_document_chunks_search_vector_gin', table_name='document_chunks', postgresql_using='gin')
    op.drop_column('document_chunks', 'search_vector')
    op.drop_column('document_chunks', 'content')
    op.drop_column('document_chunks', 'updated_at')

    op.add_column('document_chunks', sa.Column('table_id', sa.UUID(), nullable=True))
    op.add_column('document_chunks', sa.Column('page', sa.String(length=64), nullable=True))
    op.add_column('document_chunks', sa.Column('section', sa.Text(), nullable=True))
    op.add_column('document_chunks', sa.Column('text', sa.Text(), nullable=False))
    op.add_column('document_chunks', sa.Column('token_count', sa.Integer(), nullable=True))
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
    """)
    op.create_index(
        'ix_document_chunks_search_vector_gin', 'document_chunks', ['search_vector'],
        unique=False, postgresql_using='gin',
    )

    op.alter_column(
        'document_chunks', 'chunk_metadata',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'], unique=False)
    op.create_unique_constraint('uq_document_chunks_document_chunk', 'document_chunks', ['document_id', 'chunk_index'])
    op.create_foreign_key(
        'document_chunks_table_id_fkey', 'document_chunks', 'document_tables', ['table_id'], ['id'], ondelete='SET NULL',
    )

    op.execute("ALTER TABLE document_tables ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY document_tables_select_authenticated ON document_tables
        FOR SELECT TO authenticated
        USING (true)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS document_tables_select_authenticated ON document_tables")

    op.drop_constraint('document_chunks_table_id_fkey', 'document_chunks', type_='foreignkey')
    op.drop_constraint('uq_document_chunks_document_chunk', 'document_chunks', type_='unique')
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.alter_column(
        'document_chunks', 'chunk_metadata',
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=None,
        nullable=True,
    )

    op.drop_index('ix_document_chunks_search_vector_gin', table_name='document_chunks', postgresql_using='gin')
    op.drop_column('document_chunks', 'search_vector')
    op.drop_column('document_chunks', 'token_count')
    op.drop_column('document_chunks', 'text')
    op.drop_column('document_chunks', 'section')
    op.drop_column('document_chunks', 'page')
    op.drop_column('document_chunks', 'table_id')

    op.add_column('document_chunks', sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('document_chunks', sa.Column('content', sa.TEXT(), nullable=False))
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
    """)
    op.create_index(
        'ix_document_chunks_search_vector_gin', 'document_chunks', ['search_vector'],
        unique=False, postgresql_using='gin',
    )

    op.drop_index('ix_document_tables_document_id', table_name='document_tables')
    op.drop_table('document_tables')
