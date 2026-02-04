"""Add refresh_tokens table for secure session management with token rotation.

Tracks all issued refresh tokens to enable revocation and rotation.
When a new refresh token is issued, the old one is revoked.

Revision ID: 001
Revises: 
Create Date: 2025-01-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime, String, Index
from sqlalchemy.sql import func


# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the refresh_tokens table."""
    op.create_table(
        'refresh_tokens',
        sa.Column('id', String(36), primary_key=True, default=sa.text('(UUID())')),
        sa.Column('user_id', String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_jti', String(255), unique=True, nullable=False),
        sa.Column('expires_at', DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', DateTime(timezone=True), nullable=True),
        sa.Column('created_at', DateTime(timezone=True), server_default=func.now()),
    )
    
    # Create indexes
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_jti', 'refresh_tokens', ['token_jti'], unique=True)
    op.create_index('idx_refresh_tokens_expires', 'refresh_tokens', ['expires_at'])


def downgrade() -> None:
    """Drop the refresh_tokens table."""
    op.drop_table('refresh_tokens')
