"""align source_documents with shared corpus design

Revision ID: b7baf07266dd
Revises: 186443db98ec
Create Date: 2026-08-02 22:19:32.942626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7baf07266dd'
down_revision: Union[str, Sequence[str], None] = '186443db98ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('source_documents_user_id_fkey', 'source_documents', type_='foreignkey')
    op.drop_column('source_documents', 'user_id')
    op.add_column('source_documents', sa.Column('primary_document', sa.String(length=255), nullable=False))
    op.add_column('source_documents', sa.Column('source_url', sa.Text(), nullable=False))
    op.add_column('source_documents', sa.Column('markdown_content', sa.Text(), nullable=True))
    op.add_column('source_documents', sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column(
        'source_documents',
        'accession_number',
        existing_type=sa.VARCHAR(length=25),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'source_documents',
        'accession_number',
        existing_type=sa.String(length=32),
        type_=sa.VARCHAR(length=25),
        existing_nullable=False,
    )
    op.drop_column('source_documents', 'ingested_at')
    op.drop_column('source_documents', 'markdown_content')
    op.drop_column('source_documents', 'source_url')
    op.drop_column('source_documents', 'primary_document')
    op.add_column('source_documents', sa.Column('user_id', sa.UUID(), nullable=False))
    op.create_foreign_key(
        'source_documents_user_id_fkey', 'source_documents', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )
