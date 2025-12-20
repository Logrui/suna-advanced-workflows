"""Composio Trigger Component - Configure External Service Triggers."""

from __future__ import annotations

from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import MessageTextInput
from lfx.io import Output
from lfx.schema.data import Data


class ComposioTriggerComponent(Component):
    """Configure Composio-based triggers for external services.

    Set up webhooks and event listeners for GitHub, Slack, Gmail,
    and other services integrated via Composio.
    """

    display_name: str = "Composio Trigger"
    description: str = "Configure triggers for external services via Composio."
    documentation: str = "https://docs.kortix.com/triggers"
    icon = "Zap"
    name = "ComposioTrigger"

    inputs = [
        MessageTextInput(
            name="service",
            display_name="Service",
            info="The service to trigger from: github, slack, gmail, etc.",
            value="github",
        ),
        MessageTextInput(
            name="event_type",
            display_name="Event Type",
            info="The event type to listen for (e.g., push, pull_request, message).",
            value="push",
        ),
        MessageTextInput(
            name="connection_id",
            display_name="Connection ID",
            info="Composio connection ID for the authenticated service.",
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

    async def configure_trigger(self) -> Data:
        """Configure the Composio trigger."""
        service = self.service or "github"
        event_type = self.event_type or "push"
        connection_id = self.connection_id

        config = {
            "service": service,
            "event_type": event_type,
            "connection_id": connection_id,
            "filter": self.filter,
            "status": "scaffold",
            "webhook_url": None,
            "message": (
                f"Trigger configuration for {service}:{event_type} - "
                "implement actual Composio integration."
            ),
        }

        return Data(data=config)
