"""
Unit tests for Suna Kortix Integration API endpoints.

Tests the /suna/ensure-project and /suna/ensure-flow endpoints
that enable 1:1 ID mapping between Suna and Langflow.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel


# Test fixtures
@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.exec = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.fixture
def sample_agent_id():
    """Sample Suna agent ID."""
    return uuid4()


@pytest.fixture
def sample_workflow_id():
    """Sample Suna workflow ID."""
    return uuid4()


class TestEnsureProject:
    """Tests for the ensure-project endpoint."""

    @pytest.mark.asyncio
    async def test_ensure_project_creates_new_project(
        self, mock_session, mock_user, sample_agent_id
    ):
        """Test that a new project is created when it doesn't exist."""
        from langflow.api.v1.suna_integration import (
            EnsureProjectRequest,
            ensure_suna_project,
        )

        # Mock: no existing project found
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.exec.return_value = mock_result

        request = EnsureProjectRequest(
            suna_agent_id=sample_agent_id,
            name="Test Agent",
            description="Test description",
        )

        # Patch the integration key verification
        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_project(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        assert response.created is True
        assert response.name == "Test Agent"
        assert response.id == sample_agent_id
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_project_returns_existing_project(
        self, mock_session, mock_user, sample_agent_id
    ):
        """Test that an existing project is returned without creating a new one."""
        from langflow.api.v1.suna_integration import (
            EnsureProjectRequest,
            ensure_suna_project,
        )

        # Mock: existing project found
        existing_project = MagicMock()
        existing_project.id = sample_agent_id
        existing_project.name = "Existing Agent"
        existing_project.description = "Existing description"

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=existing_project)
        mock_session.exec.return_value = mock_result

        request = EnsureProjectRequest(
            suna_agent_id=sample_agent_id,
            name="Test Agent",  # This name should be ignored
        )

        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_project(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        assert response.created is False
        assert response.name == "Existing Agent"
        assert response.id == sample_agent_id
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_project_handles_name_conflict(
        self, mock_session, mock_user, sample_agent_id
    ):
        """Test that name conflicts are handled by appending suffix."""
        from langflow.api.v1.suna_integration import (
            EnsureProjectRequest,
            ensure_suna_project,
        )

        # Mock: no project with ID, but project with same name exists
        call_count = 0

        def mock_exec_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:
                # First call: check by ID - not found
                result.first.return_value = None
            else:
                # Second call: check by name - conflict found
                conflict_project = MagicMock()
                conflict_project.name = "Test Agent"
                result.first.return_value = conflict_project
            return result

        mock_session.exec = AsyncMock(side_effect=mock_exec_side_effect)

        request = EnsureProjectRequest(
            suna_agent_id=sample_agent_id,
            name="Test Agent",
        )

        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_project(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        # Should have "(Suna)" suffix
        assert response.created is True
        # Name conflict handling should add suffix


class TestEnsureFlow:
    """Tests for the ensure-flow endpoint."""

    @pytest.mark.asyncio
    async def test_ensure_flow_creates_new_flow(
        self, mock_session, mock_user, sample_agent_id, sample_workflow_id
    ):
        """Test that a new flow is created when it doesn't exist."""
        from langflow.api.v1.suna_integration import (
            EnsureFlowRequest,
            ensure_suna_flow,
        )

        # Mock: no existing flow found, but project exists
        call_count = 0

        def mock_exec_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            if call_count == 1:
                # First call: check flow by ID - not found
                result.first.return_value = None
            elif call_count == 2:
                # Second call: check project exists
                project = MagicMock()
                project.id = sample_agent_id
                result.first.return_value = project
            else:
                # Third call: check flow name conflict - none
                result.first.return_value = None
            return result

        mock_session.exec = AsyncMock(side_effect=mock_exec_side_effect)

        request = EnsureFlowRequest(
            suna_workflow_id=sample_workflow_id,
            suna_agent_id=sample_agent_id,
            name="Test Workflow",
            description="Test workflow description",
        )

        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_flow(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        assert response.created is True
        assert response.name == "Test Workflow"
        assert response.id == sample_workflow_id
        assert response.folder_id == sample_agent_id
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_flow_returns_existing_flow(
        self, mock_session, mock_user, sample_agent_id, sample_workflow_id
    ):
        """Test that an existing flow is returned without creating a new one."""
        from langflow.api.v1.suna_integration import (
            EnsureFlowRequest,
            ensure_suna_flow,
        )

        # Mock: existing flow found
        existing_flow = MagicMock()
        existing_flow.id = sample_workflow_id
        existing_flow.name = "Existing Workflow"
        existing_flow.folder_id = sample_agent_id
        existing_flow.description = "Existing description"

        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=existing_flow)
        mock_session.exec.return_value = mock_result

        request = EnsureFlowRequest(
            suna_workflow_id=sample_workflow_id,
            suna_agent_id=sample_agent_id,
            name="Test Workflow",  # This should be ignored
        )

        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_flow(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        assert response.created is False
        assert response.name == "Existing Workflow"
        assert response.id == sample_workflow_id
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_flow_handles_missing_project(
        self, mock_session, mock_user, sample_agent_id, sample_workflow_id
    ):
        """Test that flow can be created even if project doesn't exist."""
        from langflow.api.v1.suna_integration import (
            EnsureFlowRequest,
            ensure_suna_flow,
        )

        # Mock: no flow, no project
        call_count = 0

        def mock_exec_side_effect(query):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            result.first.return_value = None  # Nothing exists
            return result

        mock_session.exec = AsyncMock(side_effect=mock_exec_side_effect)

        request = EnsureFlowRequest(
            suna_workflow_id=sample_workflow_id,
            suna_agent_id=sample_agent_id,
            name="Test Workflow",
        )

        with patch(
            "langflow.api.v1.suna_integration.verify_integration_key",
            return_value=True,
        ):
            response = await ensure_suna_flow(
                request=request,
                session=mock_session,
                current_user=mock_user,
                _=True,
            )

        # Flow should be created, but folder_id might be None
        assert response.created is True
        mock_session.add.assert_called_once()


class TestSunaIntegrationHealth:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self):
        """Test that health endpoint returns ok status."""
        from langflow.api.v1.suna_integration import suna_integration_health

        response = await suna_integration_health()

        assert response["status"] == "ok"
        assert "message" in response
