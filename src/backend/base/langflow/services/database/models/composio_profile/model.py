"""Composio Profile database model for storing user OAuth connection profiles.

This model stores encrypted configuration for Composio toolkit connections,
enabling users to maintain multiple connection profiles per toolkit
(e.g., "Personal Gmail", "Work Gmail").
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, func, Text, Boolean, Index

if TYPE_CHECKING:
    from langflow.services.database.models.user.model import User


def utc_now():
    return datetime.now(timezone.utc)


class ComposioProfileBase(SQLModel):
    """Base model for Composio profiles with shared fields."""
    
    toolkit_slug: str = Field(
        max_length=100,
        description="Composio toolkit identifier (e.g., 'gmail', 'slack')"
    )
    profile_name: str = Field(
        max_length=255,
        description="User-defined name for this profile (e.g., 'Personal Gmail')"
    )
    display_name: str | None = Field(
        default=None,
        max_length=255,
        description="Display name shown in UI"
    )


class ComposioProfile(ComposioProfileBase, table=True):  # type: ignore[call-arg]
    """Database table for storing Composio connection profiles.
    
    Each profile represents a user's authenticated connection to a 
    Composio toolkit. Config data (including MCP URL and connection IDs)
    is stored encrypted.
    
    Attributes:
        id: Unique profile identifier
        user_id: Foreign key to the user who owns this profile
        toolkit_slug: Identifier for the Composio toolkit
        profile_name: User-defined name (unique per user+toolkit)
        encrypted_config: Fernet-encrypted JSON containing:
            - type: "composio"
            - toolkit_slug: str
            - mcp_url: str
            - connected_account_id: str
            - user_id: str (Composio's internal user ID)
        config_hash: SHA256 hash for deduplication
        connected_account_id: Composio's connected account ID (for status checks)
        is_connected: Whether the OAuth flow has been completed
        is_active: Soft delete flag
        is_default: Whether this is the default profile for the toolkit
    """
    
    __tablename__ = "composio_profile"
    
    id: UUID | None = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique profile identifier"
    )
    
    # User relationship
    user_id: UUID = Field(
        description="User ID who owns this profile",
        foreign_key="user.id",
        index=True,
        nullable=False
    )
    user: "User" = Relationship(back_populates="composio_profiles")
    
    # Encrypted configuration
    encrypted_config: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Fernet-encrypted JSON configuration"
    )
    config_hash: str = Field(
        max_length=64,
        description="SHA256 hash of config for deduplication"
    )
    
    # Composio references (stored separately for quick status checks)
    connected_account_id: str | None = Field(
        default=None,
        max_length=100,
        description="Composio connected account ID",
        index=True
    )
    
    # State flags
    is_connected: bool = Field(
        default=False,
        sa_column=Column(Boolean, default=False, nullable=False),
        description="Whether OAuth flow is complete"
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, default=True, nullable=False),
        description="Soft delete flag"
    )
    is_default: bool = Field(
        default=False,
        sa_column=Column(Boolean, default=False, nullable=False),
        description="Default profile for this toolkit"
    )
    
    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=True),
        description="Profile creation time"
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Last modification time"
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Last time profile was used for tool execution"
    )
    
    # Table-level constraints and indexes defined via __table_args__
    __table_args__ = (
        # Unique constraint: one profile name per user per toolkit
        Index(
            "ix_composio_profile_user_toolkit_name",
            "user_id", "toolkit_slug", "profile_name",
            unique=True
        ),
        # Index for active profiles by user
        Index(
            "ix_composio_profile_user_active",
            "user_id", "is_active"
        ),
    )


class ComposioProfileCreate(ComposioProfileBase):
    """Schema for creating a new Composio profile."""
    
    encrypted_config: str = Field(description="Fernet-encrypted JSON configuration")
    config_hash: str = Field(description="SHA256 hash of config")
    connected_account_id: str | None = None
    is_connected: bool = False
    is_default: bool = False


class ComposioProfileRead(SQLModel):
    """Schema for reading Composio profile data (without encrypted config)."""
    
    id: UUID
    user_id: UUID
    toolkit_slug: str
    profile_name: str
    display_name: str | None
    connected_account_id: str | None
    is_connected: bool
    is_active: bool
    is_default: bool
    created_at: datetime | None
    updated_at: datetime | None
    last_used_at: datetime | None


class ComposioProfileUpdate(SQLModel):
    """Schema for updating a Composio profile."""
    
    profile_name: str | None = None
    display_name: str | None = None
    is_connected: bool | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    connected_account_id: str | None = None
    # Note: encrypted_config updates should go through dedicated methods


class ComposioProfileWithMcpUrl(ComposioProfileRead):
    """Extended read schema that includes decrypted MCP URL (for internal use)."""
    
    mcp_url: str | None = None
