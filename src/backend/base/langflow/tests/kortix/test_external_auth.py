"""
Unit tests for External Auth API endpoints.

Tests the /external-auth/issue-token endpoint that enables
Suna Kortix to obtain session tokens for its authenticated users.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException


# Test fixtures
@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.username = "suna_abc12345"
    user.is_active = True
    return user


@pytest.fixture
def valid_integration_key():
    """Return a valid integration key for testing."""
    return "test-integration-secret-key"


class TestVerifyIntegrationKey:
    """Tests for integration key verification."""

    @pytest.mark.asyncio
    async def test_valid_integration_key_passes(self, valid_integration_key):
        """Test that a valid integration key passes verification."""
        from langflow.api.v1.external_auth import verify_integration_key

        with patch.dict(
            os.environ, {"LANGFLOW_EXTERNAL_AUTH_SECRET": valid_integration_key}
        ):
            result = await verify_integration_key(x_integration_key=valid_integration_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_invalid_integration_key_raises_401(self, valid_integration_key):
        """Test that an invalid integration key raises 401."""
        from langflow.api.v1.external_auth import verify_integration_key

        with patch.dict(
            os.environ, {"LANGFLOW_EXTERNAL_AUTH_SECRET": valid_integration_key}
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_integration_key(x_integration_key="wrong-key")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_secret_raises_500(self):
        """Test that missing secret configuration raises 500."""
        from langflow.api.v1.external_auth import verify_integration_key

        # Ensure the env var is not set
        with patch.dict(os.environ, {}, clear=True):
            if "LANGFLOW_EXTERNAL_AUTH_SECRET" in os.environ:
                del os.environ["LANGFLOW_EXTERNAL_AUTH_SECRET"]
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_integration_key(x_integration_key="any-key")
            assert exc_info.value.status_code == 500


class TestFindOrCreateExternalUser:
    """Tests for the find_or_create_external_user function."""

    @pytest.mark.asyncio
    async def test_finds_existing_user(self, mock_db_session, mock_user):
        """Test that an existing user is returned."""
        from langflow.api.v1.external_auth import find_or_create_external_user

        with patch(
            "langflow.api.v1.external_auth.get_user_by_username",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            result = await find_or_create_external_user(
                db=mock_db_session,
                external_user_id="abc123def456",
                email="test@example.com",
                username="suna_abc12345",
                source="suna-kortix",
            )

            assert result == mock_user
            mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_user_when_not_found(self, mock_db_session):
        """Test that a new user is created when none exists."""
        from langflow.api.v1.external_auth import find_or_create_external_user

        with patch(
            "langflow.api.v1.external_auth.get_user_by_username",
            new_callable=AsyncMock,
            return_value=None,  # No existing user
        ):
            with patch(
                "langflow.api.v1.external_auth.get_password_hash",
                return_value="hashed_password",
            ):
                result = await find_or_create_external_user(
                    db=mock_db_session,
                    external_user_id="abc123def456",
                    email="test@example.com",
                    username="suna_abc12345",
                    source="suna-kortix",
                )

                # User should be created
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_username_from_external_id(self, mock_db_session):
        """Test username generation from external user ID."""
        from langflow.api.v1.external_auth import find_or_create_external_user

        with patch(
            "langflow.api.v1.external_auth.get_user_by_username",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "langflow.api.v1.external_auth.get_password_hash",
                return_value="hashed_password",
            ):
                result = await find_or_create_external_user(
                    db=mock_db_session,
                    external_user_id="long-external-user-id-12345",
                    email=None,
                    username=None,  # No username provided
                    source="suna-kortix",
                )

                # Should generate username: suna-kortix_long-ext
                mock_db_session.add.assert_called_once()


class TestIssueToken:
    """Tests for the issue-token endpoint."""

    @pytest.mark.asyncio
    async def test_issue_token_for_new_user(self, valid_integration_key, mock_user):
        """Test issuing token for a new external user."""
        from langflow.api.v1.external_auth import (
            ExternalUserRequest,
            issue_token_for_external_user,
        )

        mock_tokens = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
        }

        with patch.dict(
            os.environ, {"LANGFLOW_EXTERNAL_AUTH_SECRET": valid_integration_key}
        ):
            with patch(
                "langflow.api.v1.external_auth.session_scope",
            ) as mock_scope:
                mock_db = AsyncMock()
                mock_scope.return_value.__aenter__.return_value = mock_db

                with patch(
                    "langflow.api.v1.external_auth.find_or_create_external_user",
                    new_callable=AsyncMock,
                    return_value=mock_user,
                ):
                    with patch(
                        "langflow.api.v1.external_auth.create_user_tokens",
                        new_callable=AsyncMock,
                        return_value=mock_tokens,
                    ):
                        request = ExternalUserRequest(
                            external_user_id="abc123def456",
                            email="test@example.com",
                            source="suna-kortix",
                        )

                        response = await issue_token_for_external_user(
                            request=request,
                            _=True,  # Integration key verified
                        )

                        assert response.access_token == "test-access-token"
                        assert response.refresh_token == "test-refresh-token"
                        assert response.token_type == "bearer"


class TestExternalAuthHealth:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_configured_when_secret_set(self, valid_integration_key):
        """Test health endpoint when secret is configured."""
        from langflow.api.v1.external_auth import external_auth_health

        with patch.dict(
            os.environ, {"LANGFLOW_EXTERNAL_AUTH_SECRET": valid_integration_key}
        ):
            response = await external_auth_health()
            assert response["status"] == "ok"
            assert response["configured"] is True

    @pytest.mark.asyncio
    async def test_health_returns_not_configured_when_secret_missing(self):
        """Test health endpoint when secret is not configured."""
        from langflow.api.v1.external_auth import external_auth_health

        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            env_copy = os.environ.copy()
            if "LANGFLOW_EXTERNAL_AUTH_SECRET" in env_copy:
                del env_copy["LANGFLOW_EXTERNAL_AUTH_SECRET"]
            
            with patch.dict(os.environ, env_copy, clear=True):
                response = await external_auth_health()
                assert response["status"] == "ok"
                assert response["configured"] is False
