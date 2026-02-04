"""Add vacation_periods, vacation_allocations tables and related columns.

Creates company-level vacation year configuration and per-user vacation day tracking.
Adds vacation_period_id and days_count columns to vacation_requests table.

Revision ID: 002
Revises: 001
Create Date: 2025-02-04 10:00:00.000000
"""

from datetime import date, datetime
from typing import Optional
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import DateTime, String, Date, Boolean, Float, Index, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create vacation_periods and vacation_allocations tables, add columns to vacation_requests."""
    # Create vacation_periods table
    _create_vacation_periods_table()
    
    # Create vacation_allocations table
    _create_vacation_allocations_table()
    
    # Add columns to vacation_requests table
    _add_columns_to_vacation_requests()
    
    # Seed default vacation periods for existing companies
    _seed_vacation_periods()


def downgrade() -> None:
    """Drop vacation_allocations and vacation_periods tables, remove columns from vacation_requests."""
    # Remove columns from vacation_requests (use batch for SQLite compatibility)
    with op.batch_alter_table('vacation_requests') as batch_op:
        batch_op.drop_column('vacation_period_id')
        batch_op.drop_column('days_count')
    
    # Drop indexes on vacation_allocations
    op.execute('DROP INDEX IF EXISTS idx_vacation_allocations_unique')
    op.execute('DROP INDEX IF EXISTS idx_vacation_allocations_period')
    op.execute('DROP INDEX IF EXISTS idx_vacation_allocations_user')
    
    # Drop vacation_allocations table
    op.drop_table('vacation_allocations')
    
    # Drop indexes on vacation_periods
    op.execute('DROP INDEX IF EXISTS idx_vacation_periods_dates')
    op.execute('DROP INDEX IF EXISTS idx_vacation_periods_company')
    
    # Drop vacation_periods table
    op.drop_table('vacation_periods')


def _create_vacation_periods_table() -> None:
    """Create the vacation_periods table."""
    op.create_table(
        'vacation_periods',
        sa.Column('id', String(36), primary_key=True, default=sa.text('(UUID())')),
        sa.Column('company_id', String(36), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', String(100), nullable=False),
        sa.Column('start_date', Date, nullable=False),
        sa.Column('end_date', Date, nullable=False),
        sa.Column('is_default', Boolean, default=False),
        sa.Column('created_at', DateTime(timezone=True), server_default=func.now()),
        sa.Column('updated_at', DateTime(timezone=True), server_default=func.now()),
    )
    
    # Create indexes
    op.create_index('idx_vacation_periods_company', 'vacation_periods', ['company_id'])
    op.create_index('idx_vacation_periods_dates', 'vacation_periods', ['company_id', 'start_date', 'end_date'])


def _create_vacation_allocations_table() -> None:
    """Create the vacation_allocations table."""
    op.create_table(
        'vacation_allocations',
        sa.Column('id', String(36), primary_key=True, default=sa.text('(UUID())')),
        sa.Column('user_id', String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vacation_period_id', String(36), sa.ForeignKey('vacation_periods.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_days', Float, default=25.0),
        sa.Column('carried_over_days', Float, default=0.0),
        sa.Column('days_used', Float, default=0.0),
        sa.Column('created_at', DateTime(timezone=True), server_default=func.now()),
        sa.Column('updated_at', DateTime(timezone=True), server_default=func.now()),
    )
    
    # Create indexes
    op.create_index('idx_vacation_allocations_user', 'vacation_allocations', ['user_id'])
    op.create_index('idx_vacation_allocations_period', 'vacation_allocations', ['vacation_period_id'])
    # Create unique constraint for user_id + vacation_period_id
    op.execute('CREATE UNIQUE INDEX idx_vacation_allocations_unique ON vacation_allocations(user_id, vacation_period_id)')


def _add_columns_to_vacation_requests() -> None:
    """Add vacation_period_id and days_count columns to vacation_requests table."""
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('vacation_requests') as batch_op:
        batch_op.add_column(sa.Column('vacation_period_id', String(36), sa.ForeignKey('vacation_periods.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('days_count', Float, nullable=True))
    
    # Create index on vacation_period_id (after the column is added)
    op.create_index('idx_vacation_requests_period', 'vacation_requests', ['vacation_period_id'])


def _seed_vacation_periods() -> None:
    """Seed default vacation periods for all existing companies.
    
    Creates a default vacation period for each company if none exist.
    Default period: April 1 of current year to March 31 of next year.
    """
    connection = op.get_bind()
    
    # Get all companies
    result = connection.execute(sa.text("SELECT id, name FROM companies"))
    companies = result.fetchall()
    
    if not companies:
        return
    
    # Calculate default period dates (April 1 - March 31)
    current_year = datetime.now().year
    start_date = date(current_year, 4, 1)
    end_date = date(current_year + 1, 3, 31)
    period_name = f"{current_year}-{current_year + 1}"
    
    for company_id, company_name in companies:
        # Check if company already has vacation periods
        check_result = connection.execute(
            sa.text("SELECT COUNT(*) FROM vacation_periods WHERE company_id = :company_id"),
            {"company_id": company_id}
        )
        count = check_result.scalar()
        
        if count > 0:
            continue
        
        # Insert default vacation period
        connection.execute(
            sa.text("""
                INSERT INTO vacation_periods (id, company_id, name, start_date, end_date, is_default, created_at, updated_at)
                VALUES (:id, :company_id, :name, :start_date, :end_date, true, :created_at, :updated_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "company_id": company_id,
                "name": period_name,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        )
