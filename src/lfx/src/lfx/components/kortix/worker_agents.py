"""Suna Worker Component - Invoke a Suna Kortix Agent Worker."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput, MultilineInput, SecretStrInput
from lfx.io import Output
from lfx.schema.message import Message


class SunaWorkerComponent(Component):
    """Invoke a Suna Kortix Agent Worker to perform tasks.

    This component allows you to send messages to a Suna Worker (AI Agent)
    and receive responses. Workers can execute tools, search the web,
    write code, and more.
    """

    display_name: str = "Suna Worker"
    description: str = "Send a task to a Suna Kortix Agent Worker and get a response."
    documentation: str = "https://docs.kortix.ai/workers"
    icon = "Bot"
    name = "SunaWorker"
    

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
            name="agent_id",
            display_name="Agent ID",
            info="The ID of the Suna Agent to use. Leave empty to use the default agent.",
            advanced=True,
        ),
        MessageTextInput(
            name="thread_id",
            display_name="Thread ID",
            info="Optional thread ID for conversation continuity. Leave empty to create a new thread.",
            advanced=True,
        ),
        MultilineInput(
            name="task",
            display_name="Task",
            info="The task or message to send to the Suna Worker.",
            required=True,
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="execute_worker"),
    ]

    async def execute_worker(self) -> Message:
        """Execute the Suna Worker with the given task."""
        import httpx

        task = self.task or "Hello, Suna!"
        agent_id = self.agent_id or "default"
        api_base_url = (self.api_base_url or "http://localhost:8000").rstrip("/")
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key

        payload = {
            "input": task,
            "thread_id": self.thread_id,
            "agent_id": agent_id,
            "stream": False
        }

        try:
            # Try the standard Suna/Langflow run endpoint or a specific agent run endpoint
            # We'll use a likely endpoint pattern for Suna agents
            url = f"{api_base_url}/v1/agents/{agent_id}/run"
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Handle various response formats
                if isinstance(data, dict):
                    # Suna/Langflow often returns "output" or "result"
                    result_text = data.get("output") or data.get("result") or data.get("message") or str(data)
                else:
                    result_text = str(data)
                
                return Message(text=str(result_text))
                
        except Exception as e:
             return Message(text=f"Error invoking Suna Worker: {str(e)}\nURL: {url}")
