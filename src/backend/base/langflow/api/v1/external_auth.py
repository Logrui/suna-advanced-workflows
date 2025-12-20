"""External authentication API for integration with parent applications like Suna.

This module provides a secure way for external applications to obtain session tokens
for their authenticated users without requiring them to go through the normal login flow.
"""

import os
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from lfx.log.logger import logger
from pydantic import BaseModel, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession

from langflow.services.auth.utils import create_user_tokens, get_password_hash
from langflow.services.database.models.user.crud import get_user_by_username
from langflow.services.database.models.user.model import User
from langflow.services.deps import session_scope

router = APIRouter(prefix="/external-auth", tags=["External Auth"])


class ExternalUserRequest(BaseModel):
    """Request to create or get token for an external user."""

    external_user_id: str  # User ID from parent system (Suna)
    email: Optional[EmailStr] = None
    username: Optional[str] = None  # Fallback if email not provided
    source: Optional[str] = "suna-kortix"  # Identify the calling application


class TokenResponse(BaseModel):
    """Token response for external auth."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


def get_integration_secret() -> str:
    """Get the integration secret from environment."""
    secret = os.getenv("LANGFLOW_EXTERNAL_AUTH_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="External auth not configured",
        )
    return secret


async def verify_integration_key(
    x_integration_key: str = Header(..., alias="X-Integration-Key"),
) -> bool:
    """Verify the integration key from the parent application."""
    expected_secret = get_integration_secret()
    if x_integration_key != expected_secret:
        logger.warning("Invalid integration key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid integration key"
        )
    return True


async def find_or_create_external_user(
    db: AsyncSession,
    external_user_id: str,
    email: Optional[str] = None,
    username: Optional[str] = None,
    source: Optional[str] = "suna-kortix",
) -> User:
    """Find existing user or create a new one for external auth."""
    # Generate a unique username based on external ID
    lookup_username = username or f"{source}_{external_user_id[:8]}"

    # Try to find existing user
    user = await get_user_by_username(db, lookup_username)

    if user:
        logger.debug(f"Found existing external user: {lookup_username}")
        return user

    # Create new user
    logger.info(f"Creating new external user: {lookup_username}")

    # Generate a random password (user won't use it - auth is via parent app)
    random_password = get_password_hash(str(uuid4()))

    new_user = User(
        username=lookup_username,
        password=random_password,
        is_active=True,
        is_superuser=False,
        profile_image=None,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/issue-token", response_model=TokenResponse)
async def issue_token_for_external_user(
    request: ExternalUserRequest,
    _: bool = Depends(verify_integration_key),
) -> TokenResponse:
    """Issue an access token for an external user.

    This endpoint is called by the parent application (Suna) to obtain
    session tokens for an authenticated user. The parent app must provide
    a valid integration key.

    Flow:
    1. Suna user authenticates with Supabase
    2. Suna backend calls this endpoint with user info
    3. Advanced Workflows backend creates/finds user and issues token
    4. Suna frontend embeds Advanced Workflows iframe with token
    """
    logger.info(
        f"[External Auth] issue-token called: external_user_id={request.external_user_id[:8]}..., "
        f"email={request.email}, source={request.source}"
    )
    async with session_scope() as db:
        # Find or create the user
        user = await find_or_create_external_user(
            db=db,
            external_user_id=request.external_user_id,
            email=request.email,
            username=request.username,
            source=request.source,
        )

        # Create tokens for the user
        tokens = await create_user_tokens(user.id, db)

        logger.info(f"Issued token for external user: {user.username}")

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_type=tokens.get("token_type", "bearer"),
        )


@router.get("/health")
async def external_auth_health():
    """Health check for external auth endpoint."""
    has_secret = bool(os.getenv("LANGFLOW_EXTERNAL_AUTH_SECRET"))
    return {
        "status": "ok",
        "configured": has_secret,
    }
