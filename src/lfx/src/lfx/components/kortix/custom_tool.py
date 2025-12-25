"""Custom Tool Component - Define and execute custom tools for Kortix Agents."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import BoolInput, MessageTextInput, MultilineInput, SecretStrInput
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
        ),
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
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        api_key = getattr(self, "api_key", None)
        if api_key:
            headers["X-API-Key"] = api_key
        return headers

    def _get_base_url(self) -> str:
        """Get the API base URL."""
        return (getattr(self, "api_base_url", None) or "http://localhost:8000").rstrip("/")

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
        if self.register_tool and self.api_key:
            import httpx

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self._get_base_url()}/v1/tools/custom",
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
