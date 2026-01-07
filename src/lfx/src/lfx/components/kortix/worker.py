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

    def _fetch_agents(self) -> list[dict]:
        """Fetch available agents from the Kortix API."""
        import os
        import httpx
        import json

        print("[KortixAgent._fetch_agents] === FETCH AGENTS CALLED ===")
        
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        print(f"[KortixAgent._fetch_agents] KORTIX_INTERNAL_SECRET present: {bool(internal_secret)}")
        
        if not internal_secret:
            print("[KortixAgent._fetch_agents] ERROR: No KORTIX_INTERNAL_SECRET - returning empty list")
            return []

        base_url = self._get_base_url()
        print(f"[KortixAgent._fetch_agents] Base URL: {base_url}")
        
        headers = self._get_headers()
        print(f"[KortixAgent._fetch_agents] Headers: {json.dumps({k: ('***' if 'secret' in k.lower() else v) for k, v in headers.items()}, indent=2)}")

        url = f"{base_url}/agents"
        print(f"[KortixAgent._fetch_agents] Full URL: {url}")

        try:
            with httpx.Client(timeout=10.0) as client:
                print(f"[KortixAgent._fetch_agents] Making GET request...")
                response = client.get(url, headers=headers)
                
                print(f"[KortixAgent._fetch_agents] Response status: {response.status_code}")
                print(f"[KortixAgent._fetch_agents] Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                
                raw_text = response.text
                print(f"[KortixAgent._fetch_agents] Raw response text (first 500 chars): {raw_text[:500]}")
                
                data = response.json()
                print(f"[KortixAgent._fetch_agents] Parsed JSON type: {type(data)}")
                print(f"[KortixAgent._fetch_agents] Parsed JSON keys (if dict): {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                print(f"[KortixAgent._fetch_agents] Full response data: {json.dumps(data, indent=2) if len(json.dumps(data)) < 2000 else 'Response too large'}")

                # Handle different response formats
                if isinstance(data, list):
                    print(f"[KortixAgent._fetch_agents] Response is a list with {len(data)} items")
                    print(f"[KortixAgent._fetch_agents] Returning list directly")
                    return data
                elif isinstance(data, dict):
                    # Could be paginated: {"agents": [...]} or {"data": [...]}
                    agents = data.get("agents", data.get("data", data.get("items", [])))
                    print(f"[KortixAgent._fetch_agents] Response is a dict. Extracted agents: {type(agents)} with length {len(agents) if isinstance(agents, list) else 'N/A'}")
                    print(f"[KortixAgent._fetch_agents] Extracted agents data: {json.dumps(agents, indent=2) if agents and len(json.dumps(agents)) < 2000 else 'Empty or too large'}")
                    return agents
                
                print(f"[KortixAgent._fetch_agents] WARNING: Unexpected data type - returning empty list")
                return []
        except httpx.HTTPStatusError as e:
            print(f"[KortixAgent._fetch_agents] HTTP ERROR {e.response.status_code}: {e}")
            print(f"[KortixAgent._fetch_agents] Error response body: {e.response.text}")
            return []
        except Exception as e:
            print(f"[KortixAgent._fetch_agents] EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            print(f"[KortixAgent._fetch_agents] Traceback: {traceback.format_exc()}")
            return []

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update the agent dropdown with available agents."""
        import json
        
        print(f"[KortixAgent.update_build_config] === UPDATE BUILD CONFIG CALLED ===")
        print(f"[KortixAgent.update_build_config] field_name: {field_name}")
        print(f"[KortixAgent.update_build_config] field_value: {field_value}")
        print(f"[KortixAgent.update_build_config] build_config keys: {list(build_config.keys())}")
        
        # Trigger refresh when agent_id field changes
        if field_name in {"agent_id"}:
            print(f"[KortixAgent.update_build_config] Field is agent_id - processing...")
            try:
                print(f"[KortixAgent.update_build_config] Calling _fetch_agents()...")
                agents = self._fetch_agents()
                print(f"[KortixAgent.update_build_config] _fetch_agents() returned {len(agents)} agents")

                if agents:
                    print(f"[KortixAgent.update_build_config] Processing {len(agents)} agents...")
                    # Build options list with agent names
                    # Each option will be "Agent Name (ID)" so users can see both
                    options = []
                    options_metadata = []

                    for idx, agent in enumerate(agents):
                        print(f"[KortixAgent.update_build_config] Processing agent {idx}: {json.dumps(agent, indent=2)}")
                        
                        agent_id = agent.get("id") or agent.get("agent_id") or ""
                        agent_name = agent.get("name") or agent.get("display_name") or agent_id
                        
                        print(f"[KortixAgent.update_build_config]   - agent_id: {agent_id}")
                        print(f"[KortixAgent.update_build_config]   - agent_name: {agent_name}")
                        
                        # Display format: "Agent Name (id)"
                        display_text = f"{agent_name}" if agent_name else agent_id
                        print(f"[KortixAgent.update_build_config]   - display_text: {display_text}")
                        
                        options.append(display_text)
                        
                        # Store metadata with the actual ID for execution
                        metadata = {
                            "id": agent_id,
                            "name": agent_name,
                            "description": agent.get("description", ""),
                        }
                        options_metadata.append(metadata)
                        print(f"[KortixAgent.update_build_config]   - metadata: {metadata}")

                    print(f"[KortixAgent.update_build_config] Built options list: {options}")
                    print(f"[KortixAgent.update_build_config] Setting build_config['agent_id']['options']...")
                    build_config["agent_id"]["options"] = options
                    build_config["agent_id"]["options_metadata"] = options_metadata
                    
                    # Keep selected value if it's still valid
                    current_value = build_config.get("agent_id", {}).get("value", "")
                    print(f"[KortixAgent.update_build_config] Current value: {current_value}")
                    
                    if current_value not in options:
                        new_value = options[0] if options else "-- No Agents Found --"
                        print(f"[KortixAgent.update_build_config] Current value not in options - setting to: {new_value}")
                        build_config["agent_id"]["value"] = new_value
                    else:
                        print(f"[KortixAgent.update_build_config] Current value is valid - keeping it")
                    
                    print(f"[KortixAgent.update_build_config] Final agent_id config: {json.dumps(build_config.get('agent_id', {}), indent=2)}")
                else:
                    print(f"[KortixAgent.update_build_config] No agents returned - setting 'No Agents Found'")
                    build_config["agent_id"]["options"] = ["-- No Agents Found --"]
                    build_config["agent_id"]["value"] = "-- No Agents Found --"
                    
            except Exception as e:
                print(f"[KortixAgent.update_build_config] EXCEPTION: {type(e).__name__}: {e}")
                import traceback
                print(f"[KortixAgent.update_build_config] Traceback: {traceback.format_exc()}")
                build_config["agent_id"]["options"] = [f"-- Error: {str(e)[:30]} --"]
        else:
            print(f"[KortixAgent.update_build_config] field_name '{field_name}' not in trigger set - skipping")

        print(f"[KortixAgent.update_build_config] === RETURNING BUILD CONFIG ===")
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

        url = f"{api_base_url}/agents/{agent_id}/run"

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
