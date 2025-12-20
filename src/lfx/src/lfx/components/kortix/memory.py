"""Suna Memory Component - Agent Memory Operations."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import IntInput, MessageTextInput, MultilineInput, SecretStrInput
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
        SecretStrInput(
            name="api_key",
            display_name="Suna API Key",
            info="Your Suna Kortix API key. Can also be set via SUNA_API_KEY environment variable.",
            advanced=True,
        ),
        MessageTextInput(
            name="api_base_url",
            display_name="API Base URL",
            info="Base URL for the Suna API (e.g., http://localhost:8000 or https://api.kortix.ai)",
            value="http://localhost:8000",
            advanced=True,
        ),
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

    async def execute_memory_op(self) -> Data:
        """Execute the memory operation."""
        import httpx

        operation = self.operation or "search"
        agent_id = self.agent_id
        content = self.content
        limit = self.limit or 10
        api_base_url = (self.api_base_url or "http://localhost:8000").rstrip("/")

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        
        payload = {
            "agent_id": agent_id,
            "content": content,
            "memory_id": self.memory_id,
            "limit": limit
        }

        try:
            url = f"{api_base_url}/v1/memory/{operation}"
            
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
