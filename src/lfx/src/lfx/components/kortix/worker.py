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
            info="Select a Kortix Agent to use. Agents are fetched automatically on load.",
            options=[],  # Empty to trigger auto-fetch on mount
            value="",
            placeholder="-- Select an Agent --",
            refresh_button=True,
            real_time_refresh=True,
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
        """Helper to safely get user_id from the component context.
        
        Resolves the real Suna Account ID from the username if it's an external user.
        """
        # Check cache first to avoid redundant DB hits
        if hasattr(self, "_resolved_user_id") and self._resolved_user_id:
            return self._resolved_user_id

        try:
            if hasattr(self, "user_id") and self.user_id:
                # 1. Try to resolve the Suna Account ID from the username in DB
                resolved = self._resolve_user_id_from_db()
                if resolved:
                    self._resolved_user_id = resolved
                    return resolved
                
                # 2. Fallback to standard Langflow user_id
                return str(self.user_id)
        except Exception:
            pass
        return None

    def _resolve_user_id_from_db(self) -> str | None:
        """Fetch the username from the database and extract the Suna ID if prefixed."""
        try:
            from lfx.services.deps import session_scope
            from langflow.services.database.models.user.crud import get_user_by_id
            from lfx.utils.async_helpers import run_until_complete
            import uuid

            user_uuid = self.user_id
            if isinstance(user_uuid, str):
                user_uuid = uuid.UUID(user_uuid)
            
            print(f"[KortixAgent] Attempting Suna ID resolution for Langflow user_id: {user_uuid}")
            
            async def get_username():
                async with session_scope() as session:
                    user = await get_user_by_id(session, user_uuid)
                    if not user:
                        print(f"[KortixAgent] No user found in DB for ID: {user_uuid}")
                        return None
                    print(f"[KortixAgent] Found user in DB. Username: '{user.username}'")
                    return user.username
            
            username = run_until_complete(get_username())
            if username and username.startswith("suna_"):
                resolved_id = username.replace("suna_", "")
                print(f"[KortixAgent] SUCCESS: Resolved Suna Account ID from username: {resolved_id}")
                return resolved_id
            elif username:
                print(f"[KortixAgent] SKIP: Username '{username}' does not have 'suna_' prefix.")
        except Exception as e:
            print(f"[KortixAgent] ERROR in ID resolution: {e!s}")
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

    def _fetch_workflow_info(self, workflow_id: str) -> dict | None:
        """Fetch workflow info from Kortix backend to get the associated agent_id.
        
        Uses the GET /workflows/{workflow_id} endpoint which returns the workflow
        with its agent_id field.
        """
        import os
        import httpx
        
        print(f"[KortixAgent._fetch_workflow_info] Fetching workflow info for: {workflow_id}")
        
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret:
            print("[KortixAgent._fetch_workflow_info] ERROR: No KORTIX_INTERNAL_SECRET")
            return None
        
        base_url = self._get_base_url()
        url = f"{base_url}/workflows/{workflow_id}"
        headers = self._get_headers()
        
        print(f"[KortixAgent._fetch_workflow_info] URL: {url}")
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                print(f"[KortixAgent._fetch_workflow_info] Response status: {response.status_code}")
                
                if response.status_code == 404:
                    print(f"[KortixAgent._fetch_workflow_info] Workflow not found: {workflow_id}")
                    return None
                
                response.raise_for_status()
                data = response.json()
                print(f"[KortixAgent._fetch_workflow_info] Workflow data: agent_id={data.get('agent_id')}, name={data.get('name')}")
                return data
        except Exception as e:
            print(f"[KortixAgent._fetch_workflow_info] ERROR: {type(e).__name__}: {e}")
            return None

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update the agent dropdown with available agents."""
        import json
        
        print(f"[KortixAgent.update_build_config] === UPDATE BUILD CONFIG CALLED ===")
        print(f"[KortixAgent.update_build_config] field_name: {field_name}")
        print(f"[KortixAgent.update_build_config] field_value: {field_value}")
        print(f"[KortixAgent.update_build_config] build_config keys: {list(build_config.keys())}")
        
        # Trigger refresh when agent_id field changes
        if field_name in {"agent_id"} or field_name is None:
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
                    
                    # Try to auto-select agent based on workflow's agent_id
                    current_value = build_config.get("agent_id", {}).get("value", "")
                    print(f"[KortixAgent.update_build_config] Current value: {current_value}")
                    
                    # Get flow_id from build_config (same pattern as kortix_trigger.py)
                    # flow_id in LFX maps to workflow_id in Suna
                    flow_id_data = build_config.get("_frontend_node_flow_id")
                    
                    # Extract actual value - it may be a dict with 'value' key
                    if isinstance(flow_id_data, dict):
                        flow_id = flow_id_data.get('value')
                    else:
                        flow_id = flow_id_data
                    
                    # Fallback: try self.flow_id attribute
                    if not flow_id and hasattr(self, 'flow_id'):
                        flow_id = getattr(self, 'flow_id', None)
                    
                    print(f"[KortixAgent.update_build_config] flow_id (workflow_id): {flow_id}")
                    
                    # Fetch workflow info to get the associated agent_id
                    target_agent_id = None
                    if flow_id:
                        workflow_info = self._fetch_workflow_info(str(flow_id))
                        if workflow_info:
                            target_agent_id = workflow_info.get("agent_id")
                            print(f"[KortixAgent.update_build_config] Workflow's agent_id: {target_agent_id}")
                    
                    # Find and auto-select the agent matching the workflow's agent_id
                    auto_selected = False
                    if target_agent_id:
                        for idx, metadata in enumerate(options_metadata):
                            agent_id = metadata.get("id")
                            
                            # Match by agent_id
                            if agent_id == target_agent_id or str(agent_id) == str(target_agent_id):
                                new_value = options[idx]
                                print(f"[KortixAgent.update_build_config] AUTO-SELECT: '{new_value}' matches workflow agent_id {target_agent_id}")
                                build_config["agent_id"]["value"] = new_value
                                auto_selected = True
                                break
                    
                    if not auto_selected:
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
