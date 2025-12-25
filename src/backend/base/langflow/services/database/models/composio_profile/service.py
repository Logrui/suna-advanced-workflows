"""Composio Profile Service for managing user OAuth connection profiles.

This service handles CRUD operations for Composio profiles, including
encryption/decryption of sensitive configuration data.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import InvalidToken
from lfx.log.logger import logger
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from langflow.services.auth import utils as auth_utils
from langflow.services.database.models.composio_profile.model import (
    ComposioProfile,
    ComposioProfileCreate,
    ComposioProfileRead,
    ComposioProfileUpdate,
)
from langflow.services.deps import get_settings_service


class ComposioProfileService:
    """Service for managing Composio connection profiles with encrypted storage."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session.
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db
    
    # -------------------------------------------------------------------------
    # Encryption Utilities
    # -------------------------------------------------------------------------
    
    def _encrypt_config(self, config: dict[str, Any]) -> str:
        """Encrypt configuration data using Fernet encryption.
        
        Args:
            config: Dictionary containing configuration to encrypt
            
        Returns:
            Encrypted string
        """
        settings_service = get_settings_service()
        json_str = json.dumps(config, sort_keys=True)
        encrypted = auth_utils.encrypt_api_key(json_str, settings_service)
        return encrypted
    
    def _decrypt_config(self, encrypted_config: str) -> dict[str, Any]:
        """Decrypt configuration data.
        
        Args:
            encrypted_config: Encrypted configuration string
            
        Returns:
            Decrypted dictionary
            
        Raises:
            ValueError: If decryption fails
        """
        settings_service = get_settings_service()
        try:
            decrypted = auth_utils.decrypt_api_key(encrypted_config, settings_service)
            return json.loads(decrypted)
        except (InvalidToken, json.JSONDecodeError) as e:
            logger.error(f"Failed to decrypt profile config: {e}")
            raise ValueError("Failed to decrypt profile configuration") from e
    
    def _compute_config_hash(self, config: dict[str, Any]) -> str:
        """Compute SHA256 hash of configuration for deduplication.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            SHA256 hash string
        """
        json_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------
    
    async def create_profile(
        self,
        user_id: UUID,
        toolkit_slug: str,
        profile_name: str,
        mcp_url: str,
        connected_account_id: str,
        composio_user_id: str,
        display_name: str | None = None,
        is_default: bool = False,
        is_connected: bool = False,
        redirect_url: str | None = None,
    ) -> ComposioProfile:
        """Create a new Composio profile with encrypted configuration.
        
        Args:
            user_id: Langflow user ID
            toolkit_slug: Composio toolkit identifier
            profile_name: User-defined profile name
            mcp_url: Composio MCP server URL
            connected_account_id: Composio connected account ID
            composio_user_id: Composio's internal user ID
            display_name: Optional display name
            is_default: Whether this is the default profile for the toolkit
            is_connected: Whether OAuth flow is complete
            redirect_url: OAuth redirect URL (if pending)
            
        Returns:
            Created ComposioProfile instance
        """
        # Build configuration to encrypt
        config = {
            "type": "composio",
            "toolkit_slug": toolkit_slug,
            "mcp_url": mcp_url,
            "connected_account_id": connected_account_id,
            "user_id": composio_user_id,
            "redirect_url": redirect_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        encrypted_config = self._encrypt_config(config)
        config_hash = self._compute_config_hash(config)
        
        # If setting as default, unset others first
        if is_default:
            await self._unset_default_profiles(user_id, toolkit_slug)
        
        # Create profile
        profile = ComposioProfile(
            user_id=user_id,
            toolkit_slug=toolkit_slug,
            profile_name=profile_name,
            display_name=display_name or profile_name,
            encrypted_config=encrypted_config,
            config_hash=config_hash,
            connected_account_id=connected_account_id,
            is_connected=is_connected,
            is_active=True,
            is_default=is_default,
        )
        
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        
        logger.info(f"Created Composio profile '{profile_name}' for toolkit '{toolkit_slug}'")
        return profile
    
    async def get_profile(self, profile_id: UUID, user_id: UUID | None = None) -> ComposioProfile | None:
        """Get a profile by ID, optionally validating user ownership.
        
        Args:
            profile_id: Profile UUID
            user_id: Optional user ID for ownership validation
            
        Returns:
            ComposioProfile or None if not found
        """
        query = select(ComposioProfile).where(ComposioProfile.id == profile_id)
        if user_id:
            query = query.where(ComposioProfile.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_profiles(
        self,
        user_id: UUID,
        toolkit_slug: str | None = None,
        is_active: bool = True,
        is_connected: bool | None = None,
    ) -> list[ComposioProfile]:
        """List profiles for a user with optional filters.
        
        Args:
            user_id: User ID
            toolkit_slug: Optional toolkit filter
            is_active: Filter by active status (default True)
            is_connected: Optional filter by connection status
            
        Returns:
            List of matching ComposioProfile instances
        """
        query = select(ComposioProfile).where(
            ComposioProfile.user_id == user_id,
            ComposioProfile.is_active == is_active,
        )
        
        if toolkit_slug:
            query = query.where(ComposioProfile.toolkit_slug == toolkit_slug)
        
        if is_connected is not None:
            query = query.where(ComposioProfile.is_connected == is_connected)
        
        # Order by default first, then by creation date
        query = query.order_by(
            ComposioProfile.is_default.desc(),
            ComposioProfile.created_at.desc()
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_profile(
        self,
        profile_id: UUID,
        user_id: UUID,
        updates: ComposioProfileUpdate,
    ) -> ComposioProfile | None:
        """Update a profile's metadata.
        
        Args:
            profile_id: Profile to update
            user_id: User ID for ownership validation
            updates: Fields to update
            
        Returns:
            Updated profile or None if not found
        """
        profile = await self.get_profile(profile_id, user_id)
        if not profile:
            return None
        
        update_data = updates.model_dump(exclude_unset=True)
        
        # Handle is_default specially
        if update_data.get("is_default"):
            await self._unset_default_profiles(user_id, profile.toolkit_slug)
        
        # Update timestamp
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        for key, value in update_data.items():
            setattr(profile, key, value)
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile
    
    async def delete_profile(self, profile_id: UUID, user_id: UUID) -> bool:
        """Soft delete a profile.
        
        Args:
            profile_id: Profile to delete
            user_id: User ID for ownership validation
            
        Returns:
            True if deleted, False if not found
        """
        profile = await self.get_profile(profile_id, user_id)
        if not profile:
            return False
        
        profile.is_active = False
        profile.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        logger.info(f"Soft deleted Composio profile {profile_id}")
        return True
    
    async def hard_delete_profile(self, profile_id: UUID, user_id: UUID) -> bool:
        """Permanently delete a profile.
        
        Args:
            profile_id: Profile to delete
            user_id: User ID for ownership validation
            
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(ComposioProfile).where(
            ComposioProfile.id == profile_id,
            ComposioProfile.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Permanently deleted Composio profile {profile_id}")
            return True
        return False
    
    # -------------------------------------------------------------------------
    # Runtime Methods (for tool execution)
    # -------------------------------------------------------------------------
    
    async def get_mcp_url(self, profile_id: UUID) -> str:
        """Get the decrypted MCP URL for runtime tool execution.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Decrypted MCP URL
            
        Raises:
            ValueError: If profile not found or decryption fails
        """
        profile = await self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        config = self._decrypt_config(profile.encrypted_config)
        mcp_url = config.get("mcp_url")
        
        if not mcp_url:
            raise ValueError(f"Profile {profile_id} has no MCP URL configured")
        
        # Update last_used_at
        profile.last_used_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return mcp_url
    
    async def get_decrypted_config(self, profile_id: UUID) -> dict[str, Any]:
        """Get the full decrypted configuration for a profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Decrypted configuration dictionary
            
        Raises:
            ValueError: If profile not found or decryption fails
        """
        profile = await self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        return self._decrypt_config(profile.encrypted_config)
    
    async def mark_connected(self, profile_id: UUID, user_id: UUID) -> ComposioProfile | None:
        """Mark a profile as connected after OAuth completion.
        
        Args:
            profile_id: Profile to update
            user_id: User ID for ownership validation
            
        Returns:
            Updated profile or None if not found
        """
        profile = await self.get_profile(profile_id, user_id)
        if not profile:
            return None
        
        profile.is_connected = True
        profile.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        logger.info(f"Marked Composio profile {profile_id} as connected")
        return profile
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    async def _unset_default_profiles(self, user_id: UUID, toolkit_slug: str) -> None:
        """Unset is_default for all profiles of a user+toolkit combination.
        
        Args:
            user_id: User ID
            toolkit_slug: Toolkit identifier
        """
        stmt = (
            update(ComposioProfile)
            .where(
                ComposioProfile.user_id == user_id,
                ComposioProfile.toolkit_slug == toolkit_slug,
                ComposioProfile.is_default == True,  # noqa: E712
            )
            .values(is_default=False, updated_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)
    
    async def check_name_availability(
        self,
        user_id: UUID,
        toolkit_slug: str,
        profile_name: str,
    ) -> bool:
        """Check if a profile name is available.
        
        Args:
            user_id: User ID
            toolkit_slug: Toolkit identifier
            profile_name: Proposed profile name
            
        Returns:
            True if name is available
        """
        query = select(ComposioProfile).where(
            ComposioProfile.user_id == user_id,
            ComposioProfile.toolkit_slug == toolkit_slug,
            ComposioProfile.profile_name == profile_name,
            ComposioProfile.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is None
    
    async def get_default_profile(
        self,
        user_id: UUID,
        toolkit_slug: str,
    ) -> ComposioProfile | None:
        """Get the default profile for a user+toolkit.
        
        Args:
            user_id: User ID
            toolkit_slug: Toolkit identifier
            
        Returns:
            Default profile or None
        """
        query = select(ComposioProfile).where(
            ComposioProfile.user_id == user_id,
            ComposioProfile.toolkit_slug == toolkit_slug,
            ComposioProfile.is_active == True,  # noqa: E712
            ComposioProfile.is_default == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def generate_unique_profile_name(
        self,
        user_id: UUID,
        toolkit_slug: str,
        base_name: str,
    ) -> str:
        """Generate a unique profile name relative to existing profiles.
        
        Args:
            user_id: User ID
            toolkit_slug: Toolkit identifier
            base_name: Desired name
            
        Returns:
            Unique name (e.g. "My Profile", "My Profile 1", etc.)
        """
        if await self.check_name_availability(user_id, toolkit_slug, base_name):
            return base_name
            
        # Try appending numbers until available
        counter = 1
        while True:
            new_name = f"{base_name} {counter}"
            if await self.check_name_availability(user_id, toolkit_slug, new_name):
                return new_name
            counter += 1
