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
            input_types=[],  # Disable connection dots
        ),
        # Provider display - starts as dropdown, converted to TabInput pill at runtime (Composio pattern)
        DropdownInput(
            name="provider_display",
            display_name="Provider",
            options=["No Provider"],
            value="No Provider",
            show=True,  # Always visible
            input_types=[],  # Disable connection dots
        ),
        # Trigger type display - starts as dropdown, converted to TabInput pill at runtime (Composio pattern)
        DropdownInput(
            name="trigger_type",
            display_name="Trigger Type",
            options=["—"],  # Placeholder - will be converted to TabInput dynamically
            value="—",
            show=False,  # Hidden until trigger loaded
            input_types=[],  # Disable connection dots
        ),
        PlaybookInput(
            name="playbook",
            display_name="Playbook",
            info="Instructions for the workflow. Supports {{variable_name}} to reference trigger data.",
            value="",
            input_types=[],  # Disable connection dots
        ),
        VariablePillsInput(
            name="available_variables",
            display_name="Available Variables",
            info="Click a variable to copy and insert it into your playbook.",
            value=[],
            target_field="playbook",
            target_textarea_id="textarea_playbook",
            advanced=False,
            input_types=[],  # Disable connection dots
        ),
        MultilineInput(
            name="data",
            display_name="Trigger Payload",
            info="Raw payload received from the trigger (populated at runtime).",
            advanced=True,
            input_types=[],  # Disable connection dots
        ),
    ]


    outputs = [
        Output(name="trigger_context", display_name="Trigger Context", method="build_trigger_context"),
        Output(name="playbook_rendered", display_name="Prompt", method="build_rendered_playbook"),
    ]

    def _get_headers(self, user_id: str | None = None) -> dict:
        """Get headers for internal API requests to Kortix backend."""
        import os
        headers = {"Content-Type": "application/json"}
        
        # Use internal auth with shared secret (no user API key needed)
        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if internal_secret:
            headers["X-Internal-Secret"] = internal_secret
            headers["X-Source"] = "advanced-workflows"
            
            # Use provided user_id or fall back to self.user_id
            effective_user_id = user_id or self._get_user_id()
            if effective_user_id:
                headers["X-User-Id"] = effective_user_id
        
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
            input_types=[],  # Disable connection dots
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
                input_types=[],  # Disable connection dots
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
        
        headers = self._get_headers(user_id)

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
        
        headers = self._get_headers(user_id)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/composio/triggers/schema/{trigger_slug}",
                    headers=headers
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
                            input_types=[],  # Disable connection dots
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
        """Parse and flatten the trigger payload for template substitution.
        
        The payload from Suna/Kortix has this nested structure:
        {
            "trigger_id": "...",
            "agent_id": "...",
            "trigger_type": "webhook",
            "timestamp": "...",
            "event_data": {                        # ← Composio event wrapper
                "id": "...",
                "triggerSlug": "GMAIL_NEW_GMAIL_MESSAGE",
                "payload": {                       # ← Actual email/event data
                    "from": "john@example.com",
                    "subject": "...",
                    "body": "...",
                    ...
                }
            },
            "context": {...},
            "execution_variables": {...}
        }
        
        We extract and flatten event_data.payload for easy {{variable}} access.
        """
        print(f"[KortixTrigger._parse_payload] Starting payload parsing")
        print(f"[KortixTrigger._parse_payload] self.data type: {type(self.data)}")
        print(f"[KortixTrigger._parse_payload] self.data value (first 500 chars): {str(self.data)[:500] if self.data else 'None'}")
        
        if not self.data:
            print("[KortixTrigger._parse_payload] No data received - returning empty dict")
            return {}
        
        try:
            # Step 1: Parse raw JSON string to dict
            if isinstance(self.data, str):
                print(f"[KortixTrigger._parse_payload] Parsing JSON string (length: {len(self.data)})")
                parsed = json.loads(self.data)
            else:
                print(f"[KortixTrigger._parse_payload] Data is already dict-like")
                parsed = dict(self.data)
            
            print(f"[KortixTrigger._parse_payload] Parsed top-level keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not a dict'}")
            
            # Step 2: Extract event_data (the Composio event wrapper)
            event_data = parsed.get("event_data", {})
            print(f"[KortixTrigger._parse_payload] event_data keys: {list(event_data.keys()) if isinstance(event_data, dict) else 'not a dict'}")
            
            # Step 3: Extract the actual payload (email/event data)
            composio_payload = event_data.get("payload", {})
            print(f"[KortixTrigger._parse_payload] composio_payload keys: {list(composio_payload.keys()) if isinstance(composio_payload, dict) else 'not a dict'}")
            
            # Step 4: Build flattened dict for template substitution
            flattened = {}
            
            if composio_payload and isinstance(composio_payload, dict):
                # Gmail-specific field mapping
                # Map Composio field names to user-friendly variable names
                
                # Sender (from field)
                from_field = composio_payload.get("from", "")
                flattened["sender"] = from_field
                flattened["from"] = from_field  # Also support {{from}}
                
                # Recipients (to field - may be string or list)
                to_field = composio_payload.get("to", [])
                if isinstance(to_field, list):
                    flattened["to"] = ", ".join(str(t) for t in to_field)
                else:
                    flattened["to"] = str(to_field) if to_field else ""
                
                # Message IDs
                flattened["message_id"] = composio_payload.get("messageId", "") or composio_payload.get("message_id", "")
                flattened["thread_id"] = composio_payload.get("threadId", "") or composio_payload.get("thread_id", "")
                
                # Subject
                flattened["subject"] = composio_payload.get("subject", "")
                
                # Body/message text
                flattened["message_text"] = composio_payload.get("body", "") or composio_payload.get("message", "") or composio_payload.get("text", "")
                
                # Timestamp
                flattened["message_timestamp"] = composio_payload.get("date", "") or composio_payload.get("timestamp", "")
                
                # Attachments - format as readable list
                attachments = composio_payload.get("attachments", [])
                if attachments and isinstance(attachments, list):
                    attachment_names = []
                    for att in attachments:
                        if isinstance(att, dict):
                            attachment_names.append(att.get("filename", att.get("name", "unknown")))
                        else:
                            attachment_names.append(str(att))
                    flattened["attachment_list"] = ", ".join(attachment_names) if attachment_names else "None"
                else:
                    flattened["attachment_list"] = "None"
                
                # Also include raw composio_payload fields for direct access
                for key, value in composio_payload.items():
                    if key not in flattened:
                        # Don't overwrite our mapped fields
                        flattened[key] = value
                
                print(f"[KortixTrigger._parse_payload] Flattened {len(flattened)} variables from composio_payload")
            else:
                print(f"[KortixTrigger._parse_payload] No composio_payload found, checking for direct payload structure")
                # Fallback: Maybe the payload is directly in parsed (simple webhook case)
                if "from" in parsed or "sender" in parsed or "subject" in parsed:
                    flattened = parsed.copy()
                    print(f"[KortixTrigger._parse_payload] Using parsed directly as flattened payload")
            
            # Step 5: Add metadata for advanced use cases
            flattened["_trigger_slug"] = event_data.get("triggerSlug", "") or event_data.get("type", "")
            flattened["_trigger_id"] = parsed.get("trigger_id", "")
            flattened["_timestamp"] = parsed.get("timestamp", "")
            flattened["_agent_id"] = parsed.get("agent_id", "")
            
            # Include full payload as JSON string for {{payload}} variable
            if composio_payload:
                flattened["payload"] = json.dumps(composio_payload, indent=2, ensure_ascii=False)
            else:
                flattened["payload"] = json.dumps(parsed, indent=2, ensure_ascii=False)
            
            print(f"[KortixTrigger._parse_payload] Final flattened dict has {len(flattened)} keys: {list(flattened.keys())}")
            
            # Debug: Log key values (truncated for readability)
            for key in ["sender", "subject", "message_id", "_trigger_slug"]:
                if key in flattened:
                    value_preview = str(flattened[key])[:100]
                    print(f"[KortixTrigger._parse_payload]   {key}: {value_preview}")
            
            return flattened
            
        except json.JSONDecodeError as e:
            print(f"[KortixTrigger._parse_payload] JSON decode error: {e}")
            print(f"[KortixTrigger._parse_payload] Raw data that failed: {str(self.data)[:200]}")
            return {"raw": str(self.data), "_error": f"JSON decode error: {e}"}
        except TypeError as e:
            print(f"[KortixTrigger._parse_payload] Type error: {e}")
            return {"raw": str(self.data), "_error": f"Type error: {e}"}
        except Exception as e:
            print(f"[KortixTrigger._parse_payload] Unexpected error: {e}")
            import traceback
            print(f"[KortixTrigger._parse_payload] Traceback: {traceback.format_exc()}")
            return {"raw": str(self.data), "_error": f"Unexpected error: {e}"}

    def _render_playbook(self, payload: dict) -> str:
        """Replace {{variable}} placeholders in playbook with actual values.
        
        Supports:
        - Simple variables: {{sender}}, {{subject}}
        - Nested variables: {{payload.attachments}}
        - Missing variable fallback: {{MISSING:varname}}
        """
        import re
        
        playbook = getattr(self, "playbook", "") or ""
        
        print(f"[KortixTrigger._render_playbook] Rendering playbook ({len(playbook)} chars)")
        print(f"[KortixTrigger._render_playbook] Available payload keys: {list(payload.keys())}")
        
        replacements_made = 0
        missing_vars = []
        
        def replace_var(match):
            nonlocal replacements_made, missing_vars
            var_name = match.group(1)
            
            # Support nested variables with dot notation
            value = payload
            for key in var_name.split("."):
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        missing_vars.append(var_name)
                        print(f"[KortixTrigger._render_playbook] Variable not found: {{{{{var_name}}}}}")
                        return f"{{{{MISSING:{var_name}}}}}"
                else:
                    missing_vars.append(var_name)
                    print(f"[KortixTrigger._render_playbook] Cannot traverse non-dict for: {{{{{var_name}}}}}")
                    return f"{{{{MISSING:{var_name}}}}}"
            
            # Format the value appropriately
            if isinstance(value, (dict, list)):
                result = json.dumps(value, ensure_ascii=False)
            elif value is None:
                result = ""
            else:
                result = str(value)
            
            replacements_made += 1
            print(f"[KortixTrigger._render_playbook] Replaced {{{{{var_name}}}}} -> {result[:50]}{'...' if len(result) > 50 else ''}")
            return result
        
        rendered = re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, playbook)
        
        print(f"[KortixTrigger._render_playbook] Completed: {replacements_made} replacements, {len(missing_vars)} missing")
        if missing_vars:
            print(f"[KortixTrigger._render_playbook] Missing variables: {missing_vars}")
        
        return rendered

    async def build_trigger_context(self) -> Data:
        """Build the trigger context output."""
        print(f"[KortixTrigger.build_trigger_context] Building trigger context output")
        print(f"[KortixTrigger.build_trigger_context] self.data populated: {bool(self.data)}")
        
        payload = self._parse_payload()
        
        context = {
            "trigger_type": getattr(self, "trigger_type", "Manual"),
            "linked_trigger": getattr(self, "linked_trigger", None),
            "payload": payload,
            "playbook": getattr(self, "playbook", ""),
        }
        
        print(f"[KortixTrigger.build_trigger_context] Context built with {len(payload)} payload fields")
        print(f"[KortixTrigger.build_trigger_context] trigger_type: {context['trigger_type']}")
        print(f"[KortixTrigger.build_trigger_context] linked_trigger: {context['linked_trigger']}")
        
        self.status = f"Trigger context loaded with {len(payload)} fields"
        return Data(data=context)

    async def build_rendered_playbook(self) -> Message:
        """Build the rendered playbook with variables replaced."""
        print(f"[KortixTrigger.build_rendered_playbook] Building rendered playbook output")
        print(f"[KortixTrigger.build_rendered_playbook] self.data populated: {bool(self.data)}")
        print(f"[KortixTrigger.build_rendered_playbook] self.playbook length: {len(getattr(self, 'playbook', '') or '')}")
        
        payload = self._parse_payload()
        rendered = self._render_playbook(payload)
        
        print(f"[KortixTrigger.build_rendered_playbook] Rendered playbook length: {len(rendered)}")
        print(f"[KortixTrigger.build_rendered_playbook] Rendered playbook preview (first 200 chars): {rendered[:200]}")
        
        self.status = f"Playbook rendered ({len(rendered)} chars)"
        return Message(text=rendered)

