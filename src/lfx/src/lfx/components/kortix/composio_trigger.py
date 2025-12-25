"""Composio Trigger Component - Configure External Service Triggers."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput, SecretStrInput
from lfx.io import Output
from lfx.schema.data import Data


class ComposioTriggerComponent(Component):
    """Configure Composio-based triggers for external services.

    Set up webhooks and event listeners for GitHub, Slack, Gmail,
    and other services integrated via Composio.
    """

    display_name: str = "Composio Trigger"
    description: str = "Configure triggers for external services via Composio."
    documentation: str = "https://docs.kortix.ai/triggers"
    icon = "Zap"
    name = "ComposioTrigger"

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
            name="app",
            display_name="Application",
            info="Select an application that has triggers. Click refresh to load apps.",
            options=["-- Select Application --"],
            value="-- Select Application --",
            refresh_button=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="trigger",
            display_name="Trigger",
            info="Select a trigger from the chosen application.",
            options=["-- Select Trigger --"],
            value="-- Select Trigger --",
            refresh_button=True,
        ),
        MessageTextInput(
            name="connection_id",
            display_name="Connection ID",
            info="Composio connection ID for the authenticated service.",
            advanced=True,
        ),
        MessageTextInput(
            name="filter",
            display_name="Filter",
            info="Optional filter expression for events (JSON).",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="config", display_name="Trigger Config", method="configure_trigger"),
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

    def _fetch_apps_with_triggers(self) -> list[dict]:
        """Fetch applications that have triggers from the API."""
        import httpx

        api_key = getattr(self, "api_key", None)
        if not api_key:
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/v1/composio/triggers/apps",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                # Handle response format - could be list or dict with apps key
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("apps", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            print(f"[ComposioTrigger] Failed to fetch apps: {e}")
            return []

    def _fetch_triggers_for_app(self, toolkit_slug: str) -> list[dict]:
        """Fetch triggers for a specific application."""
        import httpx

        api_key = getattr(self, "api_key", None)
        if not api_key or not toolkit_slug or toolkit_slug.startswith("--"):
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/v1/composio/triggers/apps/{toolkit_slug}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                # Handle response format
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("triggers", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            print(f"[ComposioTrigger] Failed to fetch triggers for {toolkit_slug}: {e}")
            return []

    def _get_app_slug_from_selection(self) -> str | None:
        """Extract app/toolkit slug from the dropdown selection."""
        app = getattr(self, "app", None)
        if not app or app.startswith("--"):
            return None

        # Check if stored as "Name (slug)" format
        if " (" in app and app.endswith(")"):
            return app.rsplit(" (", 1)[-1].rstrip(")")

        return app

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update dropdowns based on selections."""

        # Update apps when API key or base URL changes
        if field_name in {"api_key", "api_base_url", "app"}:
            try:
                apps = self._fetch_apps_with_triggers()
                
                if apps:
                    options = []
                    options_metadata = []
                    
                    for app in apps:
                        slug = app.get("slug") or app.get("toolkit_slug") or app.get("id") or ""
                        name = app.get("name") or app.get("display_name") or slug
                        
                        # Display as "Name (slug)" for clarity
                        display_text = f"{name} ({slug})" if name != slug else slug
                        options.append(display_text)
                        options_metadata.append({
                            "slug": slug,
                            "name": name,
                            "description": app.get("description", ""),
                        })
                    
                    build_config["app"]["options"] = options
                    build_config["app"]["options_metadata"] = options_metadata
                    
                    current_value = build_config.get("app", {}).get("value", "")
                    if current_value not in options:
                        build_config["app"]["value"] = options[0] if options else "-- No Apps Found --"
                else:
                    build_config["app"]["options"] = ["-- No Apps Found --"]
                    build_config["app"]["value"] = "-- No Apps Found --"
            except Exception as e:
                print(f"[ComposioTrigger] Error updating apps: {e}")

        # Update triggers when app changes
        if field_name in {"app", "trigger"}:
            try:
                app_slug = self._get_app_slug_from_selection()
                
                # If we can't get from instance, try from build_config
                if not app_slug:
                    app_value = build_config.get("app", {}).get("value", "")
                    if " (" in app_value and app_value.endswith(")"):
                        app_slug = app_value.rsplit(" (", 1)[-1].rstrip(")")
                    elif not app_value.startswith("--"):
                        app_slug = app_value

                triggers = self._fetch_triggers_for_app(app_slug) if app_slug else []
                
                if triggers:
                    options = []
                    options_metadata = []
                    
                    for trigger in triggers:
                        trigger_name = trigger.get("name") or trigger.get("display_name") or ""
                        trigger_id = trigger.get("id") or trigger.get("slug") or trigger_name
                        trigger_description = trigger.get("description", "")
                        
                        display_text = trigger_name or trigger_id
                        options.append(display_text)
                        options_metadata.append({
                            "id": trigger_id,
                            "name": trigger_name,
                            "description": trigger_description,
                        })
                    
                    build_config["trigger"]["options"] = options
                    build_config["trigger"]["options_metadata"] = options_metadata
                    
                    current_value = build_config.get("trigger", {}).get("value", "")
                    if current_value not in options:
                        build_config["trigger"]["value"] = options[0] if options else "-- No Triggers --"
                else:
                    build_config["trigger"]["options"] = ["-- No Triggers Found --"]
                    build_config["trigger"]["value"] = "-- No Triggers Found --"
            except Exception as e:
                print(f"[ComposioTrigger] Error updating triggers: {e}")

        return build_config

    async def configure_trigger(self) -> Data:
        """Configure the Composio trigger."""
        app = self._get_app_slug_from_selection()
        trigger = self.trigger if not self.trigger.startswith("--") else None
        connection_id = self.connection_id

        config = {
            "app": app,
            "trigger": trigger,
            "connection_id": connection_id,
            "filter": self.filter,
            "status": "configured" if all([app, trigger]) else "incomplete",
            "webhook_url": None,
            "message": (
                f"Trigger configuration for {app}/{trigger} - "
                "ready for Composio integration."
            ) if all([app, trigger]) else "Please select an application and trigger.",
        }

        return Data(data=config)
