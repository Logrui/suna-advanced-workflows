"""Kortix Agent Component - Invoke a Kortix Agent Worker."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput, MultilineInput
from lfx.io import Output
from lfx.schema.message import Message


class KortixAgentComponent(Component):
    """Invoke a Kortix Agent to perform tasks.

    This component allows you to send messages to a Kortix Agent
    and receive responses. Agents can execute tools, search the web,
    write code, and more.
    """

    display_name: str = "Kortix Agent"
    description: str = "Send a task to a Kortix Agent and their Sandbox"
    documentation: str = "https://docs.kortix.ai/agents"
    icon = "Bot"
    name = "KortixAgent"

    inputs = [
        # NOTE: API Key and Base URL now use environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        DropdownInput(
            name="agent_id",
            display_name="Agent",
            info="Select a Kortix Agent to use. Click refresh to load available agents.",
            options=["-- Select an Agent --"],
            value="-- Select an Agent --",
            refresh_button=True,
        ),
        MessageTextInput(
            name="thread_id",
            display_name="Thread ID",
            info="Optional thread ID for conversation continuity. Leave empty to create a new thread.",
        ),
        MultilineInput(
            name="task",
            display_name="Task",
            info="The task or message to send to the Kortix Agent.",
        ),
    ]

    outputs = [
        Output(name="response", display_name="Response", method="execute_agent"),
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

    def _fetch_agents(self) -> list[dict]:
        """Fetch available agents from the Kortix API."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret:
            return []

        headers = self._get_headers()

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self._get_base_url()}/v1/agents", headers=headers)
                response.raise_for_status()
                data = response.json()

                # Handle different response formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Could be paginated: {"agents": [...]} or {"data": [...]}
                    return data.get("agents", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            # Log but don't fail - just return empty list
            print(f"[KortixAgent] Failed to fetch agents: {e}")
            return []

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update the agent dropdown with available agents."""
        # Trigger refresh when agent_id field changes
        if field_name in {"agent_id"}:
            try:
                agents = self._fetch_agents()

                if agents:
                    # Build options list with agent names
                    # Each option will be "Agent Name (ID)" so users can see both
                    options = []
                    options_metadata = []

                    for agent in agents:
                        agent_id = agent.get("id") or agent.get("agent_id") or ""
                        agent_name = agent.get("name") or agent.get("display_name") or agent_id
                        
                        # Display format: "Agent Name (id)"
                        display_text = f"{agent_name}" if agent_name else agent_id
                        options.append(display_text)
                        
                        # Store metadata with the actual ID for execution
                        options_metadata.append({
                            "id": agent_id,
                            "name": agent_name,
                            "description": agent.get("description", ""),
                        })

                    build_config["agent_id"]["options"] = options
                    build_config["agent_id"]["options_metadata"] = options_metadata
                    
                    # Keep selected value if it's still valid
                    current_value = build_config.get("agent_id", {}).get("value", "")
                    if current_value not in options:
                        build_config["agent_id"]["value"] = options[0] if options else "-- No Agents Found --"
                else:
                    build_config["agent_id"]["options"] = ["-- No Agents Found --"]
                    build_config["agent_id"]["value"] = "-- No Agents Found --"
                    
            except Exception as e:
                print(f"[KortixAgent] Error updating build config: {e}")
                build_config["agent_id"]["options"] = [f"-- Error: {str(e)[:30]} --"]

        return build_config

    def _get_agent_id_from_selection(self) -> str | None:
        """Extract the actual agent ID from the dropdown selection."""
        if not self.agent_id or self.agent_id.startswith("--"):
            return None

        # Try to find matching metadata
        # The agent_id field value should match an entry in options_metadata
        # For now, we need to re-fetch to map the name back to ID
        agents = self._fetch_agents()
        
        for agent in agents:
            agent_id = agent.get("id") or agent.get("agent_id") or ""
            agent_name = agent.get("name") or agent.get("display_name") or agent_id
            
            # Match by display text
            if self.agent_id == agent_name or self.agent_id == agent_id:
                return agent_id

        # If no match found, treat the value as the ID itself
        return self.agent_id

    async def execute_agent(self) -> Message:
        """Execute the Kortix Agent with the given task."""
        import httpx

        task = self.task or "Hello, Kortix!"
        agent_id = self._get_agent_id_from_selection()
        
        if not agent_id:
            return Message(text="Error: Please select an agent from the dropdown.")
        
        api_base_url = self._get_base_url()

        headers = self._get_headers()

        payload = {
            "input": task,
            "thread_id": self.thread_id,
            "agent_id": agent_id,
            "stream": False
        }

        url = f"{api_base_url}/v1/agents/{agent_id}/run"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # Handle various response formats
                if isinstance(data, dict):
                    result_text = data.get("output") or data.get("result") or data.get("message") or str(data)
                else:
                    result_text = str(data)

                return Message(text=str(result_text))

        except Exception as e:
            return Message(text=f"Error invoking Kortix Agent: {str(e)}\nURL: {url}")
