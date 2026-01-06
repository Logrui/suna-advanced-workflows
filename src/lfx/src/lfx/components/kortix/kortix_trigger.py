"""Kortix Trigger Component - Workflow trigger configuration and context.

This component receives trigger context from Kortix when a workflow is executed
via the webhook endpoint. It displays linked trigger information and provides
variable access for downstream components.

Trigger Types:
- composio_event: Composio webhook events (Gmail, Slack, etc.)
- scheduled: Cron-based scheduled triggers (no payload)
- custom_webhook: Generic webhook triggers
"""

from __future__ import annotations

import json
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import (
    DropdownInput,
    MultilineInput,
    PlaybookInput,
    VariablePillsInput,
    TabInput,
)

from lfx.io import Output
from lfx.schema.data import Data
from lfx.schema.message import Message


class KortixTriggerComponent(Component):
    """Configure and receive trigger context for Kortix workflows.
    
    This component serves as the entry point for workflows triggered by Kortix.
    It displays the linked trigger configuration and exposes trigger variables
    for use in downstream components.
    """

    display_name: str = "Kortix Trigger"
    description: str = "Receive trigger context and variables from Kortix."
    documentation: str = "https://docs.kortix.ai/workflows/triggers"
    icon = "Zap"
    name = "KortixTrigger"

    inputs = [
        # NOTE: API Key and Base URL are now handled via environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        # No user-visible configuration needed for internal backend connection
        DropdownInput(
            name="linked_trigger",
            display_name="Linked Trigger",
            info="Triggers that will execute this workflow. Fetched automatically on load.",
            options=[],  # Empty to trigger auto-fetch on mount
            value="",
            placeholder="-- Select Linked Trigger --",
            refresh_button=True,
            real_time_refresh=True,
        ),
        # Provider display - starts as dropdown, converted to TabInput pill at runtime (Composio pattern)
        DropdownInput(
            name="provider_display",
            display_name="Provider",
            options=["No Provider"],
            value="No Provider",
            show=True,  # Always visible
        ),
        # Trigger type display - starts as dropdown, converted to TabInput pill at runtime (Composio pattern)
        DropdownInput(
            name="trigger_type",
            display_name="Trigger Type",
            options=["—"],  # Placeholder - will be converted to TabInput dynamically
            value="—",
            show=False,  # Hidden until trigger loaded
        ),
        PlaybookInput(
            name="playbook",
            display_name="Playbook",
            info="Instructions for the workflow. Supports {{variable_name}} to reference trigger data.",
            value="",
        ),
        VariablePillsInput(
            name="available_variables",
            display_name="Available Variables",
            info="Click a variable to copy and insert it into your playbook.",
            value=[],
            target_field="playbook",
            target_textarea_id="textarea_playbook",
            advanced=False,
        ),
        MultilineInput(
            name="data",
            display_name="Trigger Payload",
            info="Raw payload received from the trigger (populated at runtime).",
            advanced=True,
        ),
    ]


    outputs = [
        Output(name="trigger_context", display_name="Trigger Context", method="build_trigger_context"),
        Output(name="playbook_rendered", display_name="Prompt", method="build_rendered_playbook"),
    ]

    def _get_headers(self) -> dict:
        """Get headers for internal API requests to Kortix backend."""
        import os
        headers = {"Content-Type": "application/json"}
        
        # Use internal auth with shared secret (no user API key needed)
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret
            headers["X-Source"] = "advanced-workflows"
            # User ID will be added per-request when available
        
        return headers

    def _get_base_url(self) -> str:
        """Get the Kortix API base URL from environment."""
        import os
        return (os.getenv("KORTIX_BACKEND_URL") or "http://docker.host.internal:8000").rstrip("/")

    def _update_display_pills(self, build_config: dict, trigger_data: dict) -> None:
        """Update TabInput pill displays for trigger info.
        
        Uses the Composio pattern: dynamically create TabInput with single option
        using .to_dict() to ensure only one value is displayed as a pill.
        
        Args:
            build_config: The build configuration dict to update
            trigger_data: Trigger metadata dict containing provider_id, trigger_type, etc.
        """
        # Provider display - convert provider_id to human-readable label
        # Valid provider_id values: composio, schedule, generic_webhook
        provider_id = trigger_data.get("provider_id", "")
        provider_labels = {
            "composio": "Composio Trigger",
            "schedule": "Scheduled Trigger",
            "generic_webhook": "Generic Webhook",
        }
        provider_label = provider_labels.get(provider_id, "No Provider")
        
        # Dynamically create provider_display TabInput with single option (Composio pattern)
        provider_pill = TabInput(
            name="provider_display",
            display_name="Provider",
            options=[provider_label],
            value=provider_label,
        ).to_dict()
        provider_pill["show"] = True
        build_config["provider_display"] = provider_pill
        
        # Trigger type display - convert to human-readable label
        trigger_type = trigger_data.get("trigger_type", "")
        trigger_type_labels = {
            "webhook": "Webhook",
            "schedule": "Scheduled",
            "composio": "Composio Event",
        }
        trigger_type_label = trigger_type_labels.get(trigger_type, "")
        
        # Dynamically create trigger_type TabInput with single option (Composio pattern)
        if trigger_type_label:
            trigger_pill = TabInput(
                name="trigger_type",
                display_name="Trigger Type",
                options=[trigger_type_label],
                value=trigger_type_label,
            ).to_dict()
            trigger_pill["show"] = True
            build_config["trigger_type"] = trigger_pill
        else:
            # No trigger type - hide with placeholder
            build_config.setdefault("trigger_type", {})
            build_config["trigger_type"]["show"] = False



    def _fetch_linked_triggers(self, workflow_id: str, user_id: str | None = None) -> list[dict]:
        """Fetch triggers that are linked to this workflow."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        base_url = self._get_base_url()
        
        print(f"[KortixTrigger] _fetch_linked_triggers called")
        print(f"[KortixTrigger]   workflow_id: {workflow_id}")
        print(f"[KortixTrigger]   base_url: {base_url}")
        print(f"[KortixTrigger]   internal_secret set: {bool(internal_secret)}")
        
        if not internal_secret:
            print("[KortixTrigger] ERROR: KORTIX_INTERNAL_SECRET not set!")
            return []
        if not workflow_id:
            print("[KortixTrigger] ERROR: No workflow_id provided!")
            return []
        
        headers = self._get_headers()
        if user_id:
            headers["X-User-Id"] = user_id

        # Base URL already includes /v1 (e.g., https://api.suna.syhc.dev/v1)
        url = f"{base_url}/triggers/workflow/{workflow_id}/linked"
        print(f"[KortixTrigger] Making request to: {url}")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                print(f"[KortixTrigger] Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                triggers = data.get("triggers", [])
                print(f"[KortixTrigger] Found {len(triggers)} linked triggers")
                return triggers
        except Exception as e:
            print(f"[KortixTrigger] Failed to fetch linked triggers: {e}")
            return []


    def _fetch_trigger_variables(self, trigger_slug: str, user_id: str | None = None) -> list[dict]:
        """Fetch variable schema for a Composio trigger."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret or not trigger_slug:
            return []
        
        headers = self._get_headers()
        if user_id:
            headers["X-User-Id"] = user_id

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/v1/composio/triggers/schema/{trigger_slug}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract variables from config.properties
                config = data.get("config", {})
                properties = config.get("properties", {})
                
                variables = []
                for name, prop in properties.items():
                    variables.append({
                        "name": name,
                        "type": prop.get("type", "string"),
                        "description": prop.get("description", ""),
                    })
                return variables
        except Exception as e:
            print(f"[KortixTrigger] Failed to fetch trigger schema: {e}")
            return []

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update configuration based on selections."""
        import sys
        import logging
        
        # Force log to stderr to ensure visibility
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, force=True)
        logger = logging.getLogger("KortixTrigger")
        logger.setLevel(logging.DEBUG)
        
        # Write directly to stderr as well
        sys.stderr.write(f"[KortixTrigger] update_build_config CALLED: field_name={field_name}, field_value={field_value}\n")
        sys.stderr.flush()
        
        # Update linked triggers on initial load (field_name is None) OR when user interacts with linked_trigger
        if field_name is None or field_name in {"linked_trigger"}:
            try:
                # Get flow_id from build_config (Langflow passes it as _frontend_node_flow_id)
                flow_id_data = build_config.get("_frontend_node_flow_id")
                
                # Extract actual value - it may be a dict with 'value' key
                if isinstance(flow_id_data, dict):
                    flow_id = flow_id_data.get('value')
                else:
                    flow_id = flow_id_data
                
                # Fallback: try self.flow_id attribute
                if not flow_id and hasattr(self, 'flow_id'):
                    flow_id = getattr(self, 'flow_id', None)
                
                print(f"[KortixTrigger] Fetching linked triggers for flow_id: {flow_id}")
                
                if flow_id:
                    triggers = self._fetch_linked_triggers(flow_id)
                    
                    if triggers:
                        options = []
                        options_metadata = []
                        
                        for trigger in triggers:
                            name = trigger.get("name", trigger.get("trigger_id", "Unknown"))
                            agent_name = trigger.get("agent_name", "")
                            trigger_type = trigger.get("trigger_type", "")
                            provider_id = trigger.get("provider_id", "")
                            
                            display = f"{name}"
                            if agent_name:
                                display += f" (Agent: {agent_name})"
                            
                            options.append(display)
                            options_metadata.append({
                                "trigger_id": trigger.get("trigger_id"),
                                "trigger_slug": trigger.get("trigger_slug"),
                                "agent_name": agent_name,
                                "trigger_type": trigger_type,
                                "provider_id": provider_id,
                                "variables": trigger.get("variables", []),
                            })
                        
                        build_config["linked_trigger"]["options"] = options
                        build_config["linked_trigger"]["options_metadata"] = options_metadata
                        
                        # Auto-select first if current is invalid
                        current = build_config.get("linked_trigger", {}).get("value", "")
                        if current not in options and options:
                            build_config["linked_trigger"]["value"] = options[0]
                            current = options[0]
                        
                        # Update display pills based on current selection
                        if current in options and options_metadata:
                            idx = options.index(current)
                            if idx < len(options_metadata):
                                selected_trigger = options_metadata[idx]
                                print(f"[KortixTrigger] Selected trigger metadata: {selected_trigger}")
                                
                                # Update available variables
                                variables = selected_trigger.get("variables", [])
                                build_config["available_variables"]["value"] = variables
                                print(f"[KortixTrigger] Setting variables: {variables}")
                                
                                # Update display pills (provider + trigger type)
                                self._update_display_pills(build_config, selected_trigger)
                    else:
                        build_config["linked_trigger"]["options"] = ["-- No Linked Triggers --"]
                        build_config["linked_trigger"]["value"] = "-- No Linked Triggers --"
                        build_config["available_variables"]["value"] = []
                        # Reset display pills when no trigger using Composio pattern
                        provider_pill = TabInput(
                            name="provider_display",
                            display_name="Provider",
                            options=["No Provider"],
                            value="No Provider",
                        ).to_dict()
                        provider_pill["show"] = True
                        build_config["provider_display"] = provider_pill
                        # Hide trigger type with placeholder
                        build_config.setdefault("trigger_type", {})
                        build_config["trigger_type"]["show"] = False
                
                # When user selects a trigger, update the displays
                if field_name == "linked_trigger" and field_value:
                    options_metadata = build_config.get("linked_trigger", {}).get("options_metadata", [])
                    options = build_config.get("linked_trigger", {}).get("options", [])
                    
                    # Find the selected trigger's metadata
                    if field_value in options:
                        idx = options.index(field_value)
                        if idx < len(options_metadata):
                            selected_trigger = options_metadata[idx]
                            
                            # Update display pills (provider + trigger type)
                            self._update_display_pills(build_config, selected_trigger)
                            
                            # Update variables
                            variables = selected_trigger.get("variables", [])
                            build_config["available_variables"]["value"] = variables
                        
            except Exception as e:
                import traceback
                print(f"[KortixTrigger] Error updating build config: {e}")
                print(f"[KortixTrigger] Traceback: {traceback.format_exc()}")

        return build_config

    def _parse_payload(self) -> dict:
        """Parse the trigger payload from data field."""
        if not self.data:
            return {}
        try:
            if isinstance(self.data, str):
                return json.loads(self.data)
            return dict(self.data)
        except (json.JSONDecodeError, TypeError):
            return {"raw": self.data}

    def _render_playbook(self, payload: dict) -> str:
        """Replace {{variable}} placeholders in playbook with actual values."""
        import re
        
        playbook = getattr(self, "playbook", "") or ""
        
        def replace_var(match):
            var_name = match.group(1)
            # Support nested variables with dot notation
            value = payload
            for key in var_name.split("."):
                if isinstance(value, dict):
                    value = value.get(key, f"{{{{MISSING:{var_name}}}}}")
                else:
                    return f"{{{{MISSING:{var_name}}}}}"
            return str(value) if value is not None else ""
        
        return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, playbook)

    async def build_trigger_context(self) -> Data:
        """Build the trigger context output."""
        payload = self._parse_payload()
        
        context = {
            "trigger_type": getattr(self, "trigger_type", "Manual"),
            "linked_trigger": getattr(self, "linked_trigger", None),
            "payload": payload,
            "playbook": getattr(self, "playbook", ""),
        }
        
        self.status = f"Trigger context loaded with {len(payload)} fields"
        return Data(data=context)

    async def build_rendered_playbook(self) -> Message:
        """Build the rendered playbook with variables replaced."""
        payload = self._parse_payload()
        rendered = self._render_playbook(payload)
        
        self.status = f"Playbook rendered ({len(rendered)} chars)"
        return Message(text=rendered)
