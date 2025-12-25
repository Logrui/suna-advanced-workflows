"""Project Component - Manage Kortix Projects."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput, SecretStrInput
from lfx.io import Output
from lfx.schema.data import Data


class ProjectComponent(Component):
    """Manage Kortix projects.

    Create, retrieve, list, or delete projects. Projects contain agents,
    threads, and associated resources.
    """

    display_name: str = "Project Manager"
    description: str = "Create, retrieve, or list Kortix projects."
    documentation: str = "https://docs.kortix.ai/projects"
    icon = "FolderOpen"
    name = "ProjectManager"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Kortix API Key",
            info="Your Kortix API key in format pk_xxx:sk_xxx.",
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="api_base_url",
            display_name="API Base URL",
            info="Base URL for the Kortix API (e.g., http://localhost:8000)",
            value="http://localhost:8000",
            real_time_refresh=True,
        ),
        DropdownInput(
            name="operation",
            display_name="Operation",
            info="The project operation to perform.",
            options=["list", "get", "create", "delete"],
            value="list",
        ),
        DropdownInput(
            name="project",
            display_name="Project",
            info="Select a project (for get/delete operations). Click refresh to load projects.",
            options=["-- Select Project --"],
            value="-- Select Project --",
            refresh_button=True,
        ),
        MessageTextInput(
            name="project_name",
            display_name="New Project Name",
            info="Name for the new project (for create operation).",
            advanced=True,
        ),
        MessageTextInput(
            name="project_description",
            display_name="Project Description",
            info="Description for the new project (for create operation).",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="manage_project"),
    ]

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        api_key = getattr(self, "api_key", None)
        if api_key:
            headers["X-API-Key"] = api_key
        return headers

    def _get_base_url(self) -> str:
        """Get the API base URL."""
        return (getattr(self, "api_base_url", None) or "http://localhost:8000").rstrip("/")

    def _fetch_projects(self) -> list[dict]:
        """Fetch available projects from the API."""
        import httpx

        api_key = getattr(self, "api_key", None)
        if not api_key:
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/v1/projects",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("projects", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            print(f"[ProjectManager] Failed to fetch projects: {e}")
            return []

    def _get_project_id_from_selection(self) -> str | None:
        """Extract project ID from the dropdown selection."""
        project = getattr(self, "project", None)
        if not project or project.startswith("--"):
            return None

        # Check if stored as "Name (id)" format
        if " (" in project and project.endswith(")"):
            return project.rsplit(" (", 1)[-1].rstrip(")")

        # Try to find by name
        projects = self._fetch_projects()
        for p in projects:
            p_name = p.get("name") or p.get("display_name") or ""
            p_id = p.get("id") or p.get("project_id") or ""
            if project == p_name or project == p_id:
                return p_id

        return project

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update project dropdown."""
        if field_name in {"api_key", "api_base_url", "project"}:
            try:
                projects = self._fetch_projects()

                if projects:
                    options = []
                    options_metadata = []

                    for p in projects:
                        p_id = p.get("id") or p.get("project_id") or ""
                        p_name = p.get("name") or p.get("display_name") or p_id

                        display_text = f"{p_name} ({p_id})" if p_name != p_id else p_id
                        options.append(display_text)
                        options_metadata.append({
                            "id": p_id,
                            "name": p_name,
                            "description": p.get("description", ""),
                        })

                    build_config["project"]["options"] = options
                    build_config["project"]["options_metadata"] = options_metadata

                    current_value = build_config.get("project", {}).get("value", "")
                    if current_value not in options:
                        build_config["project"]["value"] = options[0] if options else "-- No Projects --"
                else:
                    build_config["project"]["options"] = ["-- No Projects Found --"]
            except Exception as e:
                print(f"[ProjectManager] Error updating build config: {e}")

        return build_config

    async def manage_project(self) -> Data:
        """Execute the project management operation."""
        import httpx

        operation = self.operation or "list"
        api_base_url = self._get_base_url()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if operation == "list":
                    response = await client.get(
                        f"{api_base_url}/v1/projects",
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    projects = data if isinstance(data, list) else data.get("projects", data.get("data", []))
                    return Data(data={
                        "operation": "list",
                        "count": len(projects),
                        "projects": projects,
                    })

                elif operation == "get":
                    project_id = self._get_project_id_from_selection()
                    if not project_id:
                        return Data(data={"error": "Please select a project"})

                    response = await client.get(
                        f"{api_base_url}/v1/projects/{project_id}",
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    return Data(data={
                        "operation": "get",
                        "project": response.json(),
                    })

                elif operation == "create":
                    if not self.project_name:
                        return Data(data={"error": "Project name is required"})

                    payload = {
                        "name": self.project_name,
                        "description": self.project_description or "",
                    }
                    response = await client.post(
                        f"{api_base_url}/v1/projects",
                        headers=self._get_headers(),
                        json=payload
                    )
                    response.raise_for_status()
                    return Data(data={
                        "operation": "create",
                        "project": response.json(),
                    })

                elif operation == "delete":
                    project_id = self._get_project_id_from_selection()
                    if not project_id:
                        return Data(data={"error": "Please select a project"})

                    response = await client.delete(
                        f"{api_base_url}/v1/projects/{project_id}",
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    return Data(data={
                        "operation": "delete",
                        "project_id": project_id,
                        "status": "deleted",
                    })

                else:
                    return Data(data={"error": f"Unknown operation: {operation}"})

        except Exception as e:
            return Data(data={
                "error": str(e),
                "operation": operation,
                "status": "failed",
            })
