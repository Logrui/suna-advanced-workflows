"""Thread Manager Component - Manage Suna Kortix Threads."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data


class ThreadManagerComponent(Component):
    """Manage Suna Kortix conversation threads.

    Create, retrieve, or list threads for agent conversations.
    Threads maintain conversation history and context.
    """

    display_name: str = "Thread Manager"
    description: str = "Create, retrieve, or list Suna Kortix conversation threads."
    documentation: str = "https://docs.kortix.ai/threads"
    icon = "FolderKanban"
    name = "ThreadManager"
    

    inputs = [
        # NOTE: API Key and Base URL now use environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        MessageTextInput(
            name="operation",
            display_name="Operation",
            info="The operation: create, get, list, delete",
            value="list",
        ),
        MessageTextInput(
            name="thread_id",
            display_name="Thread ID",
            info="Thread ID (for get/delete operations).",
            advanced=True,
        ),
        MessageTextInput(
            name="project_id",
            display_name="Project ID",
            info="Project ID to filter threads.",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="manage_thread"),
    ]

    def _get_headers(self) -> dict:
        """Get headers for internal API requests."""
        import os
        headers = {"Content-Type": "application/json"}
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret
            headers["X-Source"] = "advanced-workflows"
        return headers

    def _get_base_url(self) -> str:
        """Get the Kortix API base URL from environment."""
        import os
        return (os.getenv("KORTIX_BACKEND_URL") or "http://docker.host.internal:8000").rstrip("/")

    async def manage_thread(self) -> Data:
        """Execute the thread management operation."""
        import httpx

        operation = self.operation or "list"
        thread_id = self.thread_id
        project_id = self.project_id
        api_base_url = self._get_base_url()

        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if operation == "create":
                    url = f"{api_base_url}/v1/threads"
                    # Pass any extra metadata if inputs allowed, for now empty payload or check logic
                    payload = {"project_id": project_id} if project_id else {}
                    response = await client.post(url, json=payload, headers=headers)
                    
                elif operation == "get":
                    if not thread_id:
                        raise ValueError("Thread ID is required for 'get' operation.")
                    url = f"{api_base_url}/v1/threads/{thread_id}"
                    response = await client.get(url, headers=headers)
                    
                elif operation == "list":
                    url = f"{api_base_url}/v1/threads"
                    params = {}
                    if project_id:
                        params["project_id"] = project_id
                    response = await client.get(url, headers=headers, params=params)
                    
                elif operation == "delete":
                    if not thread_id:
                        raise ValueError("Thread ID is required for 'delete' operation.")
                    url = f"{api_base_url}/v1/threads/{thread_id}"
                    response = await client.delete(url, headers=headers)
                    
                else:
                    return Data(data={"error": f"Unknown operation: {operation}"})
                
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict):
                     return Data(data=data)
                else:
                     return Data(data={"result": data})

        except Exception as e:
            return Data(data={
                "error": str(e),
                "operation": operation,
                "status": "failed"
            })
