"""Composio Profiles API endpoints.

This module provides REST API endpoints for managing Composio OAuth
connection profiles, enabling users to create, list, update, and delete
profiles for various Composio toolkits.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.auth.utils import get_current_active_user
from langflow.services.database.models.composio_profile.model import (
    ComposioProfileRead,
    ComposioProfileUpdate,
)
from langflow.services.database.models.composio_profile.service import ComposioProfileService
from langflow.services.database.models.user.model import User
from lfx.log.logger import logger
from lfx.services.deps import injectable_session_scope

router = APIRouter(prefix="/composio-profiles", tags=["Composio Profiles"])


# -------------------------------------------------------------------------
# Request/Response Models
# -------------------------------------------------------------------------

class CreateProfileRequest(BaseModel):
    """Request body for creating a new Composio profile."""
    
    toolkit_slug: str = Field(
        ...,
        description="Composio toolkit identifier (e.g., 'gmail', 'slack')"
    )
    profile_name: str = Field(
        ...,
        description="User-defined name for this profile"
    )
    display_name: str | None = Field(
        None,
        description="Optional display name"
    )
    mcp_url: str = Field(
        ...,
        description="Composio MCP server URL"
    )
    connected_account_id: str = Field(
        ...,
        description="Composio connected account ID"
    )
    composio_user_id: str = Field(
        ...,
        description="Composio's internal user ID"
    )
    is_default: bool = Field(
        False,
        description="Set as default profile for this toolkit"
    )
    is_connected: bool = Field(
        False,
        description="Whether OAuth flow is complete"
    )
    redirect_url: str | None = Field(
        None,
        description="OAuth redirect URL (if pending)"
    )


class CreateProfileResponse(BaseModel):
    """Response after creating a Composio profile."""
    
    success: bool
    profile_id: str
    profile_name: str
    toolkit_slug: str
    redirect_url: str | None = None
    message: str | None = None


class ProfileListResponse(BaseModel):
    """Response containing list of profiles."""
    
    success: bool
    profiles: list[ComposioProfileRead]
    total: int


class NameAvailabilityResponse(BaseModel):
    """Response for profile name availability check."""
    
    available: bool
    message: str
    suggestions: list[str] = []


class SetDefaultResponse(BaseModel):
    """Response after setting a profile as default."""
    
    success: bool
    profile_id: str
    message: str


class DeleteProfileResponse(BaseModel):
    """Response after deleting a profile."""
    
    success: bool
    message: str


class MarkConnectedRequest(BaseModel):
    """Request to mark a profile as connected."""
    
    profile_id: str


class GetMcpUrlResponse(BaseModel):
    """Response containing MCP URL for runtime."""
    
    success: bool
    mcp_url: str
    profile_id: str
    toolkit_slug: str


class BulkDeleteRequest(BaseModel):
    """Request body for bulk deleting profiles."""
    
    profile_ids: list[str] = Field(
        ...,
        description="List of profile IDs to delete"
    )


class BulkDeleteResponse(BaseModel):
    """Response after bulk deleting profiles."""
    
    success: bool
    deleted_count: int
    failed_ids: list[str] = []
    message: str


class ToolkitGroup(BaseModel):
    """Group of profiles for a specific toolkit."""
    
    toolkit_slug: str
    toolkit_name: str
    icon_url: str | None
    profiles: list[ComposioProfileRead]


class GroupedProfilesResponse(BaseModel):
    """Response for grouped profiles by toolkit."""
    
    success: bool
    toolkits: list[ToolkitGroup]
    total_profiles: int



# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------

@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
    toolkit_slug: str | None = Query(None, description="Filter by toolkit"),
    is_connected: bool | None = Query(None, description="Filter by connection status"),
) -> ProfileListResponse:
    """List all Composio profiles for the current user.
    
    Optionally filter by toolkit and/or connection status.
    """
    service = ComposioProfileService(db)
    profiles = await service.list_profiles(
        user_id=current_user.id,
        toolkit_slug=toolkit_slug,
        is_connected=is_connected,
    )
    
    profile_reads = [
        ComposioProfileRead.model_validate(p, from_attributes=True)
        for p in profiles
    ]
    
    return ProfileListResponse(
        success=True,
        profiles=profile_reads,
        total=len(profile_reads),
    )


@router.get("/grouped", response_model=GroupedProfilesResponse)
async def get_grouped_profiles(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> GroupedProfilesResponse:
    """Get profiles grouped by toolkit."""
    service = ComposioProfileService(db)
    profiles = await service.list_profiles(user_id=current_user.id)
    
    # Group by toolkit
    grouped: dict[str, list[ComposioProfileRead]] = {}
    for profile in profiles:
        p_read = ComposioProfileRead.model_validate(profile, from_attributes=True)
        if profile.toolkit_slug not in grouped:
            grouped[profile.toolkit_slug] = []
        grouped[profile.toolkit_slug].append(p_read)
    
    # Create ToolkitGroup objects
    toolkits = []
    for slug, profile_list in grouped.items():
        toolkits.append(ToolkitGroup(
            toolkit_slug=slug,
            toolkit_name=slug.replace("-", " ").title(),
            icon_url=f"https://cdn.composio.dev/icons/{slug}.png",
            profiles=profile_list
        ))
    
    # Sort toolkits by name
    toolkits.sort(key=lambda x: x.toolkit_name)
    
    return GroupedProfilesResponse(
        success=True,
        toolkits=toolkits,
        total_profiles=len(profiles)
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_profiles(
    request: BulkDeleteRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> BulkDeleteResponse:
    """Bulk delete profiles."""
    service = ComposioProfileService(db)
    deleted_count = 0
    failed_ids = []
    
    for profile_id in request.profile_ids:
        try:
            pid = UUID(profile_id)
            if await service.delete_profile(pid, current_user.id):
                deleted_count += 1
            else:
                failed_ids.append(profile_id)
        except (ValueError, Exception):
            failed_ids.append(profile_id)
            
    return BulkDeleteResponse(
        success=True,
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        message=f"Deleted {deleted_count} profiles",
    )


@router.get("/toolkits/{toolkit_slug}/icon")
async def get_toolkit_icon(
    toolkit_slug: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict[str, str | bool]:
    """Get icon URL for a toolkit."""
    return {
        "success": True,
        "icon_url": f"https://cdn.composio.dev/icons/{toolkit_slug}.png"
    }



@router.post("", response_model=CreateProfileResponse)
async def create_profile(
    request: CreateProfileRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> CreateProfileResponse:
    """Create a new Composio profile.
    
    This stores the encrypted Composio configuration including MCP URL
    and connected account ID for later tool execution.
    """
    service = ComposioProfileService(db)
    
    # Check name availability
    is_available = await service.check_name_availability(
        user_id=current_user.id,
        toolkit_slug=request.toolkit_slug,
        profile_name=request.profile_name,
    )
    
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile name '{request.profile_name}' already exists for this toolkit"
        )
    
    try:
        profile = await service.create_profile(
            user_id=current_user.id,
            toolkit_slug=request.toolkit_slug,
            profile_name=request.profile_name,
            display_name=request.display_name,
            mcp_url=request.mcp_url,
            connected_account_id=request.connected_account_id,
            composio_user_id=request.composio_user_id,
            is_default=request.is_default,
            is_connected=request.is_connected,
            redirect_url=request.redirect_url,
        )
        
        return CreateProfileResponse(
            success=True,
            profile_id=str(profile.id),
            profile_name=profile.profile_name,
            toolkit_slug=profile.toolkit_slug,
            redirect_url=request.redirect_url,
            message="Profile created successfully",
        )
        
    except Exception as e:
        logger.error(f"Failed to create Composio profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}"
        )


@router.get("/check-name", response_model=NameAvailabilityResponse)
async def check_name_availability(
    toolkit_slug: str,
    profile_name: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> NameAvailabilityResponse:
    """Check if a profile name is available for a given toolkit."""
    service = ComposioProfileService(db)
    
    is_available = await service.check_name_availability(
        user_id=current_user.id,
        toolkit_slug=toolkit_slug,
        profile_name=profile_name,
    )
    
    suggestions = []
    if not is_available:
        # Generate suggestions
        base_name = profile_name.rstrip("0123456789").rstrip()
        existing_profiles = await service.list_profiles(
            user_id=current_user.id,
            toolkit_slug=toolkit_slug,
        )
        existing_names = {p.profile_name.lower() for p in existing_profiles}
        
        counter = 1
        while len(suggestions) < 3:
            suggested_name = f"{base_name} {counter}"
            if suggested_name.lower() not in existing_names:
                suggestions.append(suggested_name)
            counter += 1
    
    return NameAvailabilityResponse(
        available=is_available,
        message="Profile name is available" if is_available else "Profile name already exists",
        suggestions=suggestions,
    )


@router.get("/{profile_id}", response_model=ComposioProfileRead)
async def get_profile(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> ComposioProfileRead:
    """Get a specific profile by ID."""
    service = ComposioProfileService(db)
    profile = await service.get_profile(profile_id, current_user.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ComposioProfileRead.model_validate(profile, from_attributes=True)


@router.get("/{profile_id}/mcp-url", response_model=GetMcpUrlResponse)
async def get_mcp_url(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> GetMcpUrlResponse:
    """Get the MCP URL for a profile (for runtime tool execution)."""
    service = ComposioProfileService(db)
    
    profile = await service.get_profile(profile_id, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    try:
        mcp_url = await service.get_mcp_url(profile_id)
        return GetMcpUrlResponse(
            success=True,
            mcp_url=mcp_url,
            profile_id=str(profile_id),
            toolkit_slug=profile.toolkit_slug,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{profile_id}", response_model=ComposioProfileRead)
async def update_profile(
    profile_id: UUID,
    updates: ComposioProfileUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> ComposioProfileRead:
    """Update a profile's metadata."""
    service = ComposioProfileService(db)
    
    profile = await service.update_profile(profile_id, current_user.id, updates)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ComposioProfileRead.model_validate(profile, from_attributes=True)


@router.post("/{profile_id}/set-default", response_model=SetDefaultResponse)
async def set_default_profile(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> SetDefaultResponse:
    """Set a profile as the default for its toolkit."""
    service = ComposioProfileService(db)
    
    updates = ComposioProfileUpdate(is_default=True)
    profile = await service.update_profile(profile_id, current_user.id, updates)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return SetDefaultResponse(
        success=True,
        profile_id=str(profile_id),
        message=f"Profile '{profile.profile_name}' set as default for {profile.toolkit_slug}",
    )


@router.post("/{profile_id}/mark-connected", response_model=ComposioProfileRead)
async def mark_profile_connected(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
) -> ComposioProfileRead:
    """Mark a profile as connected after OAuth completion."""
    service = ComposioProfileService(db)
    
    profile = await service.mark_connected(profile_id, current_user.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return ComposioProfileRead.model_validate(profile, from_attributes=True)


@router.delete("/{profile_id}", response_model=DeleteProfileResponse)
async def delete_profile(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(injectable_session_scope)],
    permanent: bool = Query(False, description="Permanently delete instead of soft delete"),
) -> DeleteProfileResponse:
    """Delete a profile (soft delete by default)."""
    service = ComposioProfileService(db)
    
    if permanent:
        success = await service.hard_delete_profile(profile_id, current_user.id)
    else:
        success = await service.delete_profile(profile_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return DeleteProfileResponse(
        success=True,
        message="Profile deleted successfully",
    )
