"""Suna Memory Component - Agent Memory Operations."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import IntInput, MessageTextInput, MultilineInput
from lfx.io import Output
from lfx.schema.data import Data


class SunaMemoryComponent(Component):
    """Access and manage Suna Kortix Agent Memory.

    Store, retrieve, or search long-term memories that persist
    across agent sessions and conversations.
    """

    display_name: str = "Suna Memory"
    description: str = "Store, retrieve, or search Suna agent memories."
    documentation: str = "https://docs.kortix.ai/memory"
    icon = "Brain"
    name = "SunaMemory"
    

    inputs = [
        # NOTE: API Key and Base URL now use environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        MessageTextInput(
            name="operation",
            display_name="Operation",
            info="The operation: store, retrieve, search, delete",
            value="search",
        ),
        MessageTextInput(
            name="agent_id",
            display_name="Agent ID",
            info="The agent whose memory to access.",
        ),
        MultilineInput(
            name="content",
            display_name="Content",
            info="Content to store (for store operation) or search query (for search).",
        ),
        MessageTextInput(
            name="memory_id",
            display_name="Memory ID",
            info="Specific memory ID (for retrieve/delete operations).",
            advanced=True,
        ),
        IntInput(
            name="limit",
            display_name="Limit",
            info="Maximum number of memories to return (for search/list).",
            value=10,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="execute_memory_op"),
    ]

    def _get_headers(self) -> dict:
        """Get headers for internal API requests."""
        import os
        headers = {"Content-Type": "application/json"}
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret
            headers["X-Source"] = "advanced-workflows"
            # Add user context if available
            user_id = self._get_user_id()
            if user_id:
                headers["X-User-Id"] = user_id
        return headers

    def _get_user_id(self) -> str | None:
        """Helper to safely get user_id from the component context."""
        try:
            # self.user_id is available in CustomComponent base class
            if hasattr(self, "user_id") and self.user_id:
                return str(self.user_id)
        except Exception:
            pass
        return None

    def _get_base_url(self) -> str:
        """Get the Kortix API base URL from environment."""
        import os
        return (os.getenv("KORTIX_BACKEND_URL") or "http://docker.host.internal:8000").rstrip("/")

    async def execute_memory_op(self) -> Data:
        """Execute the memory operation."""
        import httpx

        operation = self.operation or "search"
        agent_id = self.agent_id
        content = self.content
        limit = self.limit or 10
        api_base_url = self._get_base_url()

        headers = self._get_headers()
        
        payload = {
            "agent_id": agent_id,
            "content": content,
            "memory_id": self.memory_id,
            "limit": limit
        }

        try:
            url = f"{api_base_url}/memory/{operation}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                # Ensure result matches Data schema expected by downstream components
                if isinstance(result, dict):
                     return Data(data=result)
                else:
                     return Data(data={"result": result})

        except Exception as e:
            return Data(data={
                "error": str(e),
                "operation": operation, 
                "status": "failed",
                "url": url if 'url' in locals() else "unknown"
            })
