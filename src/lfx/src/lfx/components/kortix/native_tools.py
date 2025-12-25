"""Native Tools Component - Select and configure built-in Kortix tools."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DropdownInput, MessageTextInput, MultiselectInput, SecretStrInput
from lfx.io import Output
from lfx.schema.data import Data


class NativeToolsComponent(Component):
    """Select and configure native Kortix tools.

    Browse and select from built-in tools like web search, file operations,
    code execution, browser automation, and more.
    """

    display_name: str = "Native Tools"
    description: str = "Select and configure built-in Kortix Agent tools."
    documentation: str = "https://docs.kortix.ai/tools/native"
    icon = "Package"
    name = "NativeTools"

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
            name="category",
            display_name="Tool Category",
            info="Filter tools by category.",
            options=["All", "Web", "Files", "Code", "Browser", "Communication", "Data"],
            value="All",
            refresh_button=True,
            real_time_refresh=True,
        ),
        MultiselectInput(
            name="selected_tools",
            display_name="Selected Tools",
            info="Select the tools to include in the agent's toolkit.",
            options=["-- Load Tools --"],
            value=[],
            refresh_button=True,
        ),
    ]

    outputs = [
        Output(name="tools", display_name="Tools Config", method="get_tools_config"),
        Output(name="tool_list", display_name="Tool List", method="list_tools"),
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

    def _fetch_native_tools(self, category: str | None = None) -> list[dict]:
        """Fetch available native tools from the API."""
        import httpx

        api_key = getattr(self, "api_key", None)
        if not api_key:
            # Return default tools if no API key
            return self._get_default_tools()

        try:
            params = {}
            if category and category != "All":
                params["category"] = category.lower()

            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self._get_base_url()}/v1/tools/native",
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("tools", data.get("data", data.get("items", [])))
                return self._get_default_tools()
        except Exception as e:
            print(f"[NativeTools] Failed to fetch tools: {e}")
            return self._get_default_tools()

    def _get_default_tools(self) -> list[dict]:
        """Return default native tools when API is unavailable."""
        return [
            {"name": "web_search", "display_name": "Web Search", "category": "web", "description": "Search the web"},
            {"name": "browser", "display_name": "Browser", "category": "browser", "description": "Automate browser"},
            {"name": "file_read", "display_name": "File Read", "category": "files", "description": "Read files"},
            {"name": "file_write", "display_name": "File Write", "category": "files", "description": "Write files"},
            {"name": "code_execute", "display_name": "Code Execute", "category": "code", "description": "Execute code"},
            {"name": "terminal", "display_name": "Terminal", "category": "code", "description": "Run terminal commands"},
        ]

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Dynamically update tool options based on category selection."""
        if field_name in {"api_key", "api_base_url", "category", "selected_tools"}:
            try:
                category = build_config.get("category", {}).get("value", "All")
                tools = self._fetch_native_tools(category if category != "All" else None)

                if tools:
                    options = []
                    for tool in tools:
                        name = tool.get("display_name") or tool.get("name") or ""
                        options.append(name)

                    build_config["selected_tools"]["options"] = options
                else:
                    build_config["selected_tools"]["options"] = ["-- No Tools Available --"]
            except Exception as e:
                print(f"[NativeTools] Error updating build config: {e}")

        return build_config

    async def get_tools_config(self) -> Data:
        """Get configuration for selected tools."""
        selected = self.selected_tools or []
        category = self.category or "All"

        # Fetch full tool details
        tools = self._fetch_native_tools(category if category != "All" else None)
        
        # Filter to selected tools
        selected_configs = []
        for tool in tools:
            name = tool.get("display_name") or tool.get("name") or ""
            if name in selected:
                selected_configs.append(tool)

        return Data(data={
            "category": category,
            "selected_count": len(selected_configs),
            "tools": selected_configs,
        })

    async def list_tools(self) -> Data:
        """List all available native tools."""
        category = self.category or "All"
        tools = self._fetch_native_tools(category if category != "All" else None)

        return Data(data={
            "category": category,
            "total_count": len(tools),
            "tools": [
                {
                    "name": t.get("name"),
                    "display_name": t.get("display_name"),
                    "category": t.get("category"),
                    "description": t.get("description", ""),
                }
                for t in tools
            ],
        })
