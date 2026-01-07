from langflow.utils.version import get_version_info

from .model import Flow


def get_webhook_component_in_flow(flow_data: dict):
    """Get webhook component in flow data."""
    if "nodes" in flow_data:
        for node in flow_data.get("nodes", []):
            if "Webhook" in node.get("id"):
                return node
    return None


def get_all_webhook_components_in_flow(flow_data: dict | None):
    """Get all webhook-capable components in flow data.
    
    This function identifies components that can receive webhook payloads.
    The payload is injected into these components via the tweaks mechanism.
    
    Supported component patterns:
    - Webhook: Standard Langflow webhook input
    - KortixTrigger: Custom Kortix trigger component for Composio events
    """
    if not flow_data:
        return []
    
    # Extensible list of component types that can receive webhook payloads
    WEBHOOK_PATTERNS = ["Webhook", "KortixTrigger"]
    
    nodes = flow_data.get("nodes", [])
    matched_components = []
    
    for node in nodes:
        node_id = node.get("id", "")
        for pattern in WEBHOOK_PATTERNS:
            if pattern in node_id:
                matched_components.append(node)
                # Debug: Log matched webhook components
                print(f"[WEBHOOK_DETECTION] Matched component: id={node_id}, pattern={pattern}")
                break
    
    # Debug: Summary of webhook detection
    print(f"[WEBHOOK_DETECTION] Found {len(matched_components)} webhook-capable components in flow (total nodes: {len(nodes)})")
    
    return matched_components


def get_components_versions(flow: Flow):
    versions: dict[str, str] = {}
    if flow.data is None:
        return versions
    nodes = flow.data.get("nodes", [])
    for node in nodes:
        data = node.get("data", {})
        data_node = data.get("node", {})
        if "lf_version" in data_node:
            versions[node["id"]] = data_node["lf_version"]
    return versions


def get_outdated_components(flow: Flow):
    component_versions = get_components_versions(flow)
    lf_version = get_version_info()["version"]
    outdated_components = []
    for key, value in component_versions.items():
        if value != lf_version:
            outdated_components.append(key)
    return outdated_components
