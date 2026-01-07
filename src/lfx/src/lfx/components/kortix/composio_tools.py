"""Composio Tool Component - Configure External Service Tools."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data


class ComposioToolsComponent(Component):
    """Configure Composio-based tools for external services.

    Set up tools and event listeners for GitHub, Slack, Gmail,
    and other services integrated via Composio.
    """

    display_name: str = "Composio Tools"
    description: str = "Configure tools for external services via Composio."
    documentation: str = "https://docs.kortix.ai/tools"
    icon = "Zap"
    name = "ComposioTools"

    inputs = [
        # NOTE: API Key and Base URL now use environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        DropdownInput(
            name="category",
            display_name="Category",
            info="Select a Composio category. Click refresh to load categories.",
            options=["-- Select Category --"],
            value="-- Select Category --",
            refresh_button=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="toolkit",
            display_name="Toolkit",
            info="Select a toolkit from the chosen category.",
            options=["-- Select Toolkit --"],
            value="-- Select Toolkit --",
            refresh_button=True,
            real_time_refresh=True,
        ),
        DropdownInput(
            name="tool",
            display_name="Tool",
            info="Select a tool from the chosen toolkit.",
            options=["-- Select Tool --"],
            value="-- Select Tool --",
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
        Output(name="config", display_name="Tool Config", method="configure_tool"),
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

    def _fetch_categories(self) -> list[str]:
        """Fetch available Composio categories from the API."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret:
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/composio/categories",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                # Handle response format - could be list or dict with categories key
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    categories = data.get("categories", data.get("data", data.get("items", [])))
                    # If categories are objects, extract names
                    if categories and isinstance(categories[0], dict):
                        return [c.get("name", c.get("slug", str(c))) for c in categories]
                    return categories
                return []
        except Exception as e:
            print(f"[ComposioTool] Failed to fetch categories: {e}")
            return []

    def _fetch_toolkits(self, category: str | None = None) -> list[dict]:
        """Fetch available toolkits, optionally filtered by category."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret:
            return []

        try:
            params = {"limit": 100}
            if category and not category.startswith("--"):
                params["category"] = category

            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/composio/toolkits",
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                # Handle response format
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("toolkits", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            print(f"[ComposioTool] Failed to fetch toolkits: {e}")
            return []

    def _fetch_tools(self, toolkit_slug: str) -> list[dict]:
        """Fetch tools for a specific toolkit."""
        import os
        import httpx

        internal_secret = os.getenv("KORTIX_INTERNAL_SECRET")
        if not internal_secret or not toolkit_slug or toolkit_slug.startswith("--"):
            return []

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self._get_base_url()}/composio/tools/list",
                    headers=self._get_headers(),
                    json={
                        "toolkit_slug": toolkit_slug,
                        "limit": 50
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Handle response format
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("tools", data.get("data", data.get("items", [])))
                return []
        except Exception as e:
            print(f"[ComposioTool] Failed to fetch tools: {e}")
            return []

    def _get_toolkit_slug_from_selection(self) -> str | None:
        """Extract toolkit slug from the dropdown selection."""
        toolkit = getattr(self, "toolkit", None)
        if not toolkit or toolkit.startswith("--"):
            return None

        # Check if stored as "Name (slug)" format
        if " (" in toolkit and toolkit.endswith(")"):
            # Extract slug from parentheses
            return toolkit.rsplit(" (", 1)[-1].rstrip(")")
        
        return toolkit

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update dropdowns based on selections."""
        
        # Update categories
        if field_name in {"category"}:
            try:
                categories = self._fetch_categories()
                if categories:
                    build_config["category"]["options"] = categories
                    current_value = build_config.get("category", {}).get("value", "")
                    if current_value not in categories:
                        build_config["category"]["value"] = categories[0] if categories else "-- No Categories --"
                else:
                    build_config["category"]["options"] = ["-- No Categories Found --"]
            except Exception as e:
                print(f"[ComposioTool] Error updating categories: {e}")

        # Update toolkits when category changes
        if field_name in {"category", "toolkit"}:
            try:
                category = build_config.get("category", {}).get("value")
                toolkits = self._fetch_toolkits(category)
                
                if toolkits:
                    options = []
                    options_metadata = []
                    
                    for tk in toolkits:
                        slug = tk.get("slug") or tk.get("id") or ""
                        name = tk.get("name") or tk.get("display_name") or slug
                        
                        # Display as "Name (slug)" for clarity
                        display_text = f"{name} ({slug})" if name != slug else slug
                        options.append(display_text)
                        options_metadata.append({
                            "slug": slug,
                            "name": name,
                            "description": tk.get("description", ""),
                        })
                    
                    build_config["toolkit"]["options"] = options
                    build_config["toolkit"]["options_metadata"] = options_metadata
                    
                    current_value = build_config.get("toolkit", {}).get("value", "")
                    if current_value not in options:
                        build_config["toolkit"]["value"] = options[0] if options else "-- No Toolkits --"
                else:
                    build_config["toolkit"]["options"] = ["-- No Toolkits Found --"]
                    build_config["toolkit"]["value"] = "-- No Toolkits Found --"
            except Exception as e:
                print(f"[ComposioTool] Error updating toolkits: {e}")

        # Update tools when toolkit changes
        if field_name in {"toolkit", "tool"}:
            try:
                toolkit_slug = self._get_toolkit_slug_from_selection()
                
                # If we can't get from instance, try from build_config
                if not toolkit_slug:
                    toolkit_value = build_config.get("toolkit", {}).get("value", "")
                    if " (" in toolkit_value and toolkit_value.endswith(")"):
                        toolkit_slug = toolkit_value.rsplit(" (", 1)[-1].rstrip(")")
                    elif not toolkit_value.startswith("--"):
                        toolkit_slug = toolkit_value

                tools = self._fetch_tools(toolkit_slug) if toolkit_slug else []
                
                if tools:
                    options = []
                    options_metadata = []
                    
                    for tool in tools:
                        tool_name = tool.get("name") or tool.get("display_name") or ""
                        tool_id = tool.get("id") or tool.get("slug") or tool_name
                        
                        display_text = tool_name or tool_id
                        options.append(display_text)
                        options_metadata.append({
                            "id": tool_id,
                            "name": tool_name,
                            "description": tool.get("description", ""),
                        })
                    
                    build_config["tool"]["options"] = options
                    build_config["tool"]["options_metadata"] = options_metadata
                    
                    current_value = build_config.get("tool", {}).get("value", "")
                    if current_value not in options:
                        build_config["tool"]["value"] = options[0] if options else "-- No Tools --"
                else:
                    build_config["tool"]["options"] = ["-- No Tools Found --"]
                    build_config["tool"]["value"] = "-- No Tools Found --"
            except Exception as e:
                print(f"[ComposioTool] Error updating tools: {e}")

        return build_config

    async def configure_tool(self) -> Data:
        """Configure the Composio Tool."""
        category = self.category if not self.category.startswith("--") else None
        toolkit = self._get_toolkit_slug_from_selection()
        tool = self.tool if not self.tool.startswith("--") else None
        connection_id = self.connection_id

        config = {
            "category": category,
            "toolkit": toolkit,
            "tool": tool,
            "connection_id": connection_id,
            "filter": self.filter,
            "status": "configured" if all([category, toolkit, tool]) else "incomplete",
            "webhook_url": None,
            "message": (
                f"Tool configuration for {category}/{toolkit}/{tool} - "
                "ready for Composio integration."
            ) if all([category, toolkit, tool]) else "Please select category, toolkit, and tool.",
        }

        return Data(data=config)
