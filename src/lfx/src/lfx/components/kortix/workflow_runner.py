"""Workflow Runner Component - Execute Sub-Workflows."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput, MultilineInput
from lfx.io import Output
from lfx.schema.data import Data


class WorkflowRunnerComponent(Component):
    """Execute another workflow as a sub-workflow.

    Invoke other Langflow/Kortix workflows by ID or name,
    passing inputs and receiving outputs.
    """

    display_name: str = "Workflow Runner"
    description: str = "Execute another workflow as a sub-workflow."
    documentation: str = "https://docs.kortix.ai/workflows"
    icon = "Workflow"
    name = "WorkflowRunner"
    

    inputs = [
        MessageTextInput(
            name="workflow_id",
            display_name="Workflow ID",
            info="The ID of the workflow to execute.",
        ),
        MessageTextInput(
            name="workflow_name",
            display_name="Workflow Name",
            info="The name of the workflow (alternative to ID).",
        ),
        MultilineInput(
            name="inputs_json",
            display_name="Inputs (JSON)",
            info="JSON object of inputs to pass to the workflow.",
            value="{}",
        ),
        MessageTextInput(
            name="output_type",
            display_name="Output Type",
            info="Expected output type: chat, data, or any.",
            value="chat",
            advanced=True,
        ),
    ]

    outputs = [
        Output(name="result", display_name="Result", method="run_workflow"),
    ]

    async def run_workflow(self) -> Data:
        """Execute the sub-workflow."""
        workflow_id = self.workflow_id
        workflow_name = self.workflow_name
        inputs_json = self.inputs_json or "{}"
        output_type = self.output_type or "chat"

        # TODO: Use self.run_flow() for actual implementation
        result = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "inputs": inputs_json,
            "output_type": output_type,
            "status": "scaffold",
            "output": None,
            "message": (
                f"Workflow execution for '{workflow_name or workflow_id}' - "
                "implement using self.run_flow() helper."
            ),
        }

        return Data(data=result)
