"""
Alembic Migration Template for Vendor Integration Tables

This is a template showing what the migration will look like.
To generate the actual migration:

1. Run: alembic revision --autogenerate -m "Add vendor integration tables"
2. Review the generated file in alembic/versions/
3. Run: alembic upgrade head

Or manually create this migration if autogenerate doesn't work.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'xxxxxxxxxxxx'  # Will be auto-generated
down_revision = 'yyyyyyyyyyyy'  # Previous revision
branch_labels = None
depends_on = None


def upgrade():
    """
    Create vendor_integrations and oauth_tokens tables
    """
    # Create vendor_integrations table
    op.create_table(
        'vendor_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vendor', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vendor_integrations_id'), 'vendor_integrations', ['id'], unique=False)
    op.create_index(op.f('ix_vendor_integrations_user_id'), 'vendor_integrations', ['user_id'], unique=False)
    
    # Create oauth_tokens table
    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_integration_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(), nullable=True, default='Bearer'),
        sa.Column('scope', sa.String(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id_from_vendor', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['vendor_integration_id'], ['vendor_integrations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oauth_tokens_id'), 'oauth_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_oauth_tokens_vendor_integration_id'), 'oauth_tokens', ['vendor_integration_id'], unique=False)


def downgrade():
    """
    Drop vendor integration tables
    """
    op.drop_index(op.f('ix_oauth_tokens_vendor_integration_id'), table_name='oauth_tokens')
    op.drop_index(op.f('ix_oauth_tokens_id'), table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
    
    op.drop_index(op.f('ix_vendor_integrations_user_id'), table_name='vendor_integrations')
    op.drop_index(op.f('ix_vendor_integrations_id'), table_name='vendor_integrations')
    op.drop_table('vendor_integrations')
