"""Add composio_profile table

Revision ID: a1b2c3d4e5f6
Revises: 182e5471b900
Create Date: 2025-12-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "182e5471b900"  # Current head: add context_id to message table
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create composio_profile table for storing user OAuth connection profiles."""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)  # type: ignore
    existing_tables = inspector.get_table_names()
    
    if "composio_profile" not in existing_tables:
        op.create_table(
            "composio_profile",
            # Primary key
            sa.Column("id", sqlmodel.sql.sqltypes.types.Uuid(), nullable=False),
            
            # User relationship
            sa.Column("user_id", sqlmodel.sql.sqltypes.types.Uuid(), nullable=False),
            
            # Toolkit and profile identification
            sa.Column("toolkit_slug", sa.String(length=100), nullable=False),
            sa.Column("profile_name", sa.String(length=255), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=True),
            
            # Encrypted configuration
            sa.Column("encrypted_config", sa.Text(), nullable=False),
            sa.Column("config_hash", sa.String(length=64), nullable=False),
            
            # Composio reference
            sa.Column("connected_account_id", sa.String(length=100), nullable=True),
            
            # State flags
            sa.Column("is_connected", sa.Boolean(), nullable=False, default=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
            
            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            
            # Constraints
            sa.PrimaryKeyConstraint("id", name="pk_composio_profile"),
            sa.ForeignKeyConstraint(
                ["user_id"], 
                ["user.id"],
            ),
        )
        
        # Create indexes
        with op.batch_alter_table("composio_profile", schema=None) as batch_op:
            # User ID index for listing profiles
            batch_op.create_index(
                "ix_composio_profile_user_id", 
                ["user_id"], 
                unique=False
            )
            
            # Connected account ID index for status lookups
            batch_op.create_index(
                "ix_composio_profile_connected_account_id",
                ["connected_account_id"],
                unique=False
            )
            
            # Unique constraint: one profile name per user per toolkit
            batch_op.create_index(
                "ix_composio_profile_user_toolkit_name",
                ["user_id", "toolkit_slug", "profile_name"],
                unique=True
            )
            
            # Composite index for active profiles by user
            batch_op.create_index(
                "ix_composio_profile_user_active",
                ["user_id", "is_active"],
                unique=False
            )


def downgrade() -> None:
    """Drop composio_profile table."""
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)  # type: ignore
    existing_tables = inspector.get_table_names()
    
    if "composio_profile" in existing_tables:
        with op.batch_alter_table("composio_profile", schema=None) as batch_op:
            batch_op.drop_index("ix_composio_profile_user_active", if_exists=True)
            batch_op.drop_index("ix_composio_profile_user_toolkit_name", if_exists=True)
            batch_op.drop_index("ix_composio_profile_connected_account_id", if_exists=True)
            batch_op.drop_index("ix_composio_profile_user_id", if_exists=True)
        
        op.drop_table("composio_profile")
