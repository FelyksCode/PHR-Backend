"""Add timezone column to users table

Revision ID: add_timezone_to_user
Revises: 
Create Date: 2025-12-30 

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_timezone_to_user'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timezone column to users table
    op.add_column('users', sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'))


def downgrade() -> None:
    # Remove timezone column from users table
    op.drop_column('users', 'timezone')
