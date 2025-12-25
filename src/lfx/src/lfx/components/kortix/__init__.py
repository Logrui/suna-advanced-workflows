from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.kortix.composio_tools import ComposioToolsComponent
    from lfx.components.kortix.composio_trigger import ComposioTriggerComponent
    from lfx.components.kortix.custom_tool import CustomToolComponent
    from lfx.components.kortix.memory import SunaMemoryComponent
    from lfx.components.kortix.native_tools import NativeToolsComponent
    from lfx.components.kortix.project import ProjectComponent
    from lfx.components.kortix.prompts import PlaybookRunnerComponent
    from lfx.components.kortix.sandbox import SandboxFileComponent
    from lfx.components.kortix.thread import ThreadManagerComponent
    from lfx.components.kortix.trigger import TriggerComponent
    from lfx.components.kortix.worker import KortixAgentComponent
    from lfx.components.kortix.workflow import WorkflowRunnerComponent

_dynamic_imports = {
    # Composio integrations
    "ComposioToolsComponent": "composio_tools",
    "ComposioTriggerComponent": "composio_trigger",
    # Core components
    "CustomToolComponent": "custom_tool",
    "KortixAgentComponent": "worker",
    "NativeToolsComponent": "native_tools",
    "ProjectComponent": "project",
    "SandboxFileComponent": "sandbox",
    "SunaMemoryComponent": "memory",
    "ThreadManagerComponent": "thread",
    "TriggerComponent": "trigger",
    "WorkflowRunnerComponent": "workflow",
    # Prompts
    "PlaybookRunnerComponent": "prompts",
}

__all__ = [
    # Composio integrations
    "ComposioToolsComponent",
    "ComposioTriggerComponent",
    # Core components
    "CustomToolComponent",
    "KortixAgentComponent",
    "NativeToolsComponent",
    "ProjectComponent",
    "SandboxFileComponent",
    "SunaMemoryComponent",
    "ThreadManagerComponent",
    "TriggerComponent",
    "WorkflowRunnerComponent",
    # Prompts
    "PlaybookRunnerComponent",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import Kortix components on attribute access."""
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)
