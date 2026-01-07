from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.kortix.composio_tools import ComposioToolsComponent
    from lfx.components.kortix.custom_tool import CustomToolComponent
    from lfx.components.kortix.kortix_trigger import KortixTriggerComponent
    from lfx.components.kortix.memory import SunaMemoryComponent
    from lfx.components.kortix.native_tools import NativeToolsComponent
    from lfx.components.kortix.project import ProjectComponent
    from lfx.components.kortix.prompts import PlaybookRunnerComponent
    from lfx.components.kortix.sandbox import SandboxFileComponent
    from lfx.components.kortix.thread import ThreadManagerComponent
    from lfx.components.kortix.worker import KortixAgentComponent
    from lfx.components.kortix.workflow import WorkflowRunnerComponent

_dynamic_imports = {
    # Composio integrations
    "ComposioToolsComponent": "composio_tools",
    # Core components
    "CustomToolComponent": "custom_tool",
    "KortixAgentComponent": "worker",
    "KortixTriggerComponent": "kortix_trigger",
    "NativeToolsComponent": "native_tools",
    "ProjectComponent": "project",
    "SandboxFileComponent": "sandbox",
    "SunaMemoryComponent": "memory",
    "ThreadManagerComponent": "thread",
    "WorkflowRunnerComponent": "workflow",
    # Prompts
    "PlaybookRunnerComponent": "prompts",
}

__all__ = [
    # Composio integrations
    "ComposioToolsComponent",
    # Core components
    "CustomToolComponent",
    "KortixAgentComponent",
    "KortixTriggerComponent",
    "NativeToolsComponent",
    "ProjectComponent",
    "SandboxFileComponent",
    "SunaMemoryComponent",
    "ThreadManagerComponent",
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
