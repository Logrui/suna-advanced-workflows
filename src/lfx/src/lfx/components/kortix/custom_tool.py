"""Custom Tool Component - Define and execute custom tools for Kortix Agents."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, MessageTextInput, MultilineInput
from lfx.io import Output
from lfx.schema.data import Data


class CustomToolComponent(Component):
    """Define custom tools that can be used by Kortix Agents.

    Create reusable tool definitions with custom logic, parameters,
    and execution behavior.
    """

    display_name: str = "Custom Tool"
    description: str = "Define and configure custom tools for Kortix Agents."
    documentation: str = "https://docs.kortix.ai/tools/custom"
    icon = "Wrench"
    name = "CustomTool"

    inputs = [
        # NOTE: API Key and Base URL now use environment variables
        # KORTIX_BACKEND_URL and KORTIX_INTERNAL_SECRET
        MessageTextInput(
            name="tool_name",
            display_name="Tool Name",
            info="Unique name for the custom tool.",
            required=True,
        ),
        MessageTextInput(
            name="tool_description",
            display_name="Tool Description",
            info="Description of what the tool does. Used by the agent to decide when to use it.",
            required=True,
        ),
        MultilineInput(
            name="parameters_schema",
            display_name="Parameters Schema",
            info="JSON schema defining the tool's input parameters.",
            value='{\n  "type": "object",\n  "properties": {\n    "input": {\n      "type": "string",\n      "description": "The input to process"\n    }\n  },\n  "required": ["input"]\n}',
        ),
        MultilineInput(
            name="code",
            display_name="Tool Code",
            info="Python code to execute when the tool is called. Use 'params' dict for inputs.",
            value="# Example tool code\nresult = f\"Processed: {params.get('input', '')}\"\nreturn result",
        ),
        BoolInput(
            name="register_tool",
            display_name="Register Tool",
            info="If enabled, register this tool with the Kortix backend for persistent use.",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="tool_config", display_name="Tool Config", method="build_tool"),
        Output(name="test_result", display_name="Test Result", method="test_tool"),
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

    async def build_tool(self) -> Data:
        """Build the custom tool configuration."""
        import json

        tool_name = self.tool_name or "custom_tool"
        tool_description = self.tool_description or "A custom tool"
        code = self.code or ""

        # Parse parameters schema
        try:
            params_schema = json.loads(self.parameters_schema or "{}")
        except json.JSONDecodeError:
            params_schema = {"type": "object", "properties": {}}

        tool_config = {
            "name": tool_name,
            "description": tool_description,
            "parameters": params_schema,
            "code": code,
            "type": "custom",
            "status": "configured",
        }

        # Register tool with backend if requested
        import os
        if self.register_tool and os.getenv("KORTIX_INTERNAL_SECRET"):
            import httpx

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self._get_base_url()}/tools/custom",
                        headers=self._get_headers(),
                        json=tool_config
                    )
                    response.raise_for_status()
                    registered = response.json()
                    tool_config["registered"] = True
                    tool_config["tool_id"] = registered.get("id")
            except Exception as e:
                tool_config["registered"] = False
                tool_config["registration_error"] = str(e)

        return Data(data=tool_config)

    async def test_tool(self) -> Data:
        """Test the custom tool with sample input."""
        import json

        code = self.code or ""
        
        # Parse parameters schema to get sample input
        try:
            params_schema = json.loads(self.parameters_schema or "{}")
            properties = params_schema.get("properties", {})
            # Create sample params from schema
            sample_params = {}
            for key, prop in properties.items():
                if prop.get("type") == "string":
                    sample_params[key] = f"sample_{key}"
                elif prop.get("type") == "number":
                    sample_params[key] = 0
                elif prop.get("type") == "boolean":
                    sample_params[key] = True
                else:
                    sample_params[key] = None
        except json.JSONDecodeError:
            sample_params = {}

        # Execute the code in a restricted environment
        try:
            local_vars = {"params": sample_params, "result": None}
            exec(code, {"__builtins__": {}}, local_vars)  # noqa: S102
            result = local_vars.get("result", "No result returned")
            
            return Data(data={
                "status": "success",
                "params": sample_params,
                "result": result,
            })
        except Exception as e:
            return Data(data={
                "status": "error",
                "error": str(e),
                "params": sample_params,
            })
