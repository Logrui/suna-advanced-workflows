"""
Suna Kortix Integration API Endpoints.

This module provides endpoints for Suna Kortix to ensure projects and flows exist
with specific IDs, enabling 1:1 mapping between:
- Suna Agents <-> Langflow Projects
- Suna Advanced Workflows <-> Langflow Flows
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from lfx.log import logger
from pydantic import BaseModel, EmailStr
from sqlmodel import select

from langflow.api.utils import CurrentActiveUser, DbSession
from langflow.api.v1.external_auth import verify_integration_key
from langflow.services.database.models.flow.model import Flow, FlowCreate, FlowRead
from langflow.services.database.models.folder.model import Folder, FolderCreate, FolderRead

router = APIRouter(prefix="/suna", tags=["Suna Kortix Integration"])


# Request Models
class EnsureProjectRequest(BaseModel):
    """Request to ensure a project exists with a specific ID."""

    suna_agent_id: UUID
    name: str
    description: str | None = None


class EnsureFlowRequest(BaseModel):
    """Request to ensure a flow exists with a specific ID."""

    suna_workflow_id: UUID
    suna_agent_id: UUID  # Maps to folder_id
    name: str
    description: str | None = None


class EnsureProjectResponse(BaseModel):
    """Response for ensure-project endpoint."""

    id: UUID
    name: str
    description: str | None = None
    created: bool  # True if newly created, False if already existed


class EnsureFlowResponse(BaseModel):
    """Response for ensure-flow endpoint."""

    id: UUID
    name: str
    folder_id: UUID | None
    description: str | None = None
    created: bool  # True if newly created, False if already existed


@router.post("/ensure-project", response_model=EnsureProjectResponse)
async def ensure_suna_project(
    *,
    request: EnsureProjectRequest,
    session: DbSession,
    current_user: CurrentActiveUser,
    _: bool = Depends(verify_integration_key),
):
    """
    Ensure a project exists with the specified Suna agent ID.

    If the project already exists, returns the existing project.
    If not, creates a new project with the Suna agent ID as the Langflow project ID.

    This enables 1:1 mapping: Suna Agent ID == Langflow Project ID
    """
    await logger.adebug(f"DEBUG_SUNA: ensure-project called: suna_agent_id={request.suna_agent_id}, name={request.name}, user={current_user.id}")
    try:
        # Check if project already exists with this ID
        await logger.adebug(f"DEBUG_SUNA: Checking if project exists: id={request.suna_agent_id}, user_id={current_user.id}")
        existing_project = (
            await session.exec(
                select(Folder).where(
                    Folder.id == request.suna_agent_id,
                    Folder.user_id == current_user.id,
                )
            )
        ).first()
        await logger.adebug(f"DEBUG_SUNA: existing_project query result: {existing_project}")

        if existing_project:
            await logger.ainfo(
                f"Project already exists for Suna agent {request.suna_agent_id}: {existing_project.name}"
            )
            return EnsureProjectResponse(
                id=existing_project.id,
                name=existing_project.name,
                description=existing_project.description,
                created=False,
            )

        # Check if a project with the same name exists (to avoid naming conflicts)
        existing_by_name = (
            await session.exec(
                select(Folder).where(
                    Folder.name == request.name,
                    Folder.user_id == current_user.id,
                )
            )
        ).first()

        project_name = request.name
        if existing_by_name:
            # Append Suna agent ID suffix to make name unique
            project_name = f"{request.name} (Suna)"
            await logger.ainfo(
                f"Project name '{request.name}' already exists, using '{project_name}'"
            )

        # Create new project with specified ID
        new_project = Folder(
            id=request.suna_agent_id,
            name=project_name,
            description=request.description,
            user_id=current_user.id,
        )

        session.add(new_project)
        await session.flush()
        await session.refresh(new_project)
        await session.commit()  # Explicitly commit to ensure persistence

        await logger.ainfo(
            f"Created new project for Suna agent {request.suna_agent_id}: {new_project.name}"
        )

        return EnsureProjectResponse(
            id=new_project.id,
            name=new_project.name,
            description=new_project.description,
            created=True,
        )

    except Exception as e:
        await logger.aerror(f"Failed to ensure project for Suna agent {request.suna_agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ensure-flow", response_model=EnsureFlowResponse)
async def ensure_suna_flow(
    *,
    request: EnsureFlowRequest,
    session: DbSession,
    current_user: CurrentActiveUser,
    _: bool = Depends(verify_integration_key),
):
    """
    Ensure a flow exists with the specified Suna workflow ID.

    If the flow already exists, returns the existing flow.
    If not, creates a new flow with the Suna workflow ID as the Langflow flow ID.

    The flow is associated with the project matching suna_agent_id (folder_id).

    This enables 1:1 mapping: Suna Workflow ID == Langflow Flow ID
    """
    await logger.adebug(f"DEBUG_SUNA: ensure-flow called: suna_workflow_id={request.suna_workflow_id}, suna_agent_id={request.suna_agent_id}, user={current_user.id}")
    try:
        # Check if flow already exists with this ID
        await logger.adebug(f"DEBUG_SUNA: Checking if flow exists: id={request.suna_workflow_id}, user_id={current_user.id}")
        existing_flow = (
            await session.exec(
                select(Flow).where(
                    Flow.id == request.suna_workflow_id,
                    Flow.user_id == current_user.id,
                )
            )
        ).first()
        await logger.adebug(f"DEBUG_SUNA: existing_flow query result: {existing_flow}")

        if existing_flow:
            await logger.ainfo(
                f"Flow already exists for Suna workflow {request.suna_workflow_id}: {existing_flow.name}"
            )
            return EnsureFlowResponse(
                id=existing_flow.id,
                name=existing_flow.name,
                folder_id=existing_flow.folder_id,
                description=existing_flow.description,
                created=False,
            )

        # Verify the project/folder exists
        project = (
            await session.exec(
                select(Folder).where(
                    Folder.id == request.suna_agent_id,
                    Folder.user_id == current_user.id,
                )
            )
        ).first()

        if not project:
            await logger.awarning(
                f"Project {request.suna_agent_id} not found, will create flow without folder"
            )

        # Check if a flow with the same name exists for this user
        # Note: unique_flow_name constraint is on (user_id, name), not per-folder
        existing_by_name = (
            await session.exec(
                select(Flow).where(
                    Flow.name == request.name,
                    Flow.user_id == current_user.id,
                )
            )
        ).first()

        flow_name = request.name
        if existing_by_name:
            # Append workflow ID suffix to guarantee uniqueness
            short_id = str(request.suna_workflow_id)[:8]
            flow_name = f"{request.name} ({short_id})"
            await logger.ainfo(
                f"Flow name '{request.name}' already exists for user, using '{flow_name}'"
            )

        # Create new flow with specified ID and a minimal default structure
        # The user will build the actual flow in the editor
        default_flow_data = {
            "nodes": [],
            "edges": [],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }

        new_flow = Flow(
            id=request.suna_workflow_id,
            name=flow_name,
            description=request.description or f"Advanced workflow from Suna Kortix",
            user_id=current_user.id,
            folder_id=request.suna_agent_id if project else None,
            data=default_flow_data,
            is_component=False,
        )

        session.add(new_flow)
        await session.flush()
        await session.refresh(new_flow)
        await session.commit()  # Explicitly commit to ensure persistence

        await logger.ainfo(
            f"Created new flow for Suna workflow {request.suna_workflow_id}: {new_flow.name} in folder {new_flow.folder_id}"
        )

        return EnsureFlowResponse(
            id=new_flow.id,
            name=new_flow.name,
            folder_id=new_flow.folder_id,
            description=new_flow.description,
            created=True,
        )

    except Exception as e:
        await logger.aerror(f"Failed to ensure flow for Suna workflow {request.suna_workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def suna_integration_health():
    """Health check for Suna integration endpoints."""
    return {"status": "ok", "message": "Suna integration endpoints are available"}


@router.get("/env-audit")
async def suna_env_audit():
    """
    Debug endpoint to verify runtime environment variables.
    Only exposes safe config flags, not secrets.
    Access via: GET /api/v1/suna/env-audit
    """
    import os
    
    return {
        "runtime_config": {
            "LANGFLOW_DEV": os.getenv("LANGFLOW_DEV", "[NOT SET]"),
            "LFX_DEV": os.getenv("LFX_DEV", "[NOT SET]"),
            "LANGFLOW_AUTO_LOGIN": os.getenv("LANGFLOW_AUTO_LOGIN", "[NOT SET]"),
            "LANGFLOW_ALEMBIC_LOG_TO_STDOUT": os.getenv("LANGFLOW_ALEMBIC_LOG_TO_STDOUT", "[NOT SET]"),
            "COMPOSIO_MODE": os.getenv("COMPOSIO_MODE", "[NOT SET]"),
            "LANGFLOW_CORS_ORIGINS": os.getenv("LANGFLOW_CORS_ORIGINS", "[NOT SET]"),
            "LANGFLOW_CORS_ALLOW_CREDENTIALS": os.getenv("LANGFLOW_CORS_ALLOW_CREDENTIALS", "[NOT SET]"),
        },
        "secrets_configured": {
            "COMPOSIO_API_KEY": "✓ Set" if os.getenv("COMPOSIO_API_KEY") else "✗ NOT SET",
            "LANGFLOW_SECRET_KEY": "✓ Set" if os.getenv("LANGFLOW_SECRET_KEY") else "✗ NOT SET",
        },
        "message": "Use this endpoint to verify runtime env vars are being passed from .env"
    }
