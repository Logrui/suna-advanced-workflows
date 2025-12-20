from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from lfx.components.kortix.composio_trigger import ComposioTriggerComponent
    from lfx.components.kortix.memory import SunaMemoryComponent
    from lfx.components.kortix.playbook_runner import PlaybookRunnerComponent
    from lfx.components.kortix.sandbox_file import SandboxFileComponent
    from lfx.components.kortix.thread_manager import ThreadManagerComponent
    from lfx.components.kortix.worker_agents import SunaWorkerComponent
    from lfx.components.kortix.workflow_runner import WorkflowRunnerComponent

_dynamic_imports = {
    "ComposioTriggerComponent": "composio_trigger",
    "SunaMemoryComponent": "memory",
    "PlaybookRunnerComponent": "playbook_runner",
    "SandboxFileComponent": "sandbox_file",
    "ThreadManagerComponent": "thread_manager",
    "SunaWorkerComponent": "worker_agents",
    "WorkflowRunnerComponent": "workflow_runner",
}

__all__ = [
    "ComposioTriggerComponent",
    "SunaMemoryComponent",
    "PlaybookRunnerComponent",
    "SandboxFileComponent",
    "ThreadManagerComponent",
    "SunaWorkerComponent",
    "WorkflowRunnerComponent",
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
