/**
 * Suna Profile Selector Component
 *
 * A premium dropdown component for selecting Composio profiles from Suna Kortix.
 * This component is used in EXTERNAL_PROFILES mode to replace the standard OAuth flow.
 *
 * Features:
 * - Fetches profiles from Suna Kortix backend
 * - Premium UI matching Suna's design system
 * - PostMessage bridge for "Manage Profiles" to open Suna's native modal
 * - Listens for profile updates from parent window
 *
 * When a profile is selected:
 * 1. The profile ID is stored in external_profile_id
 * 2. The MCP URL is fetched and stored in external_mcp_url
 * 3. The toolkit slug is stored in external_toolkit_slug
 *
 * These values are persisted with the flow and used during execution.
 */

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import {
    AlertCircle,
    CheckCircle2,
    ChevronDown,
    ExternalLink,
    Loader2,
    RefreshCw,
    Settings,
    Sparkles,
    User,
    Zap,
} from "lucide-react";
import type { handleOnNewValueType } from "@/CustomNodes/hooks/use-handle-new-value";
import { sunaApiClient, type ComposioProfileSummary, type ComposioToolkitGroup } from "@/lib/suna-api-client";
import { isSunaIntegrationAvailable, isInIframe } from "@/utils/iframe-mode";
import type { InputProps } from "../../types";

// ═══════════════════════════════════════════════════════════════════════════
// PostMessage Types for Parent-Child Communication
// ═══════════════════════════════════════════════════════════════════════════
interface SunaMessage {
    type: string;
    payload?: Record<string, unknown>;
}

const SUNA_MESSAGE_TYPES = {
    // From Langflow → Suna
    OPEN_PROFILE_MODAL: "SUNA_OPEN_PROFILE_MODAL",
    // From Suna → Langflow
    PROFILES_UPDATED: "SUNA_PROFILES_UPDATED",
    MODAL_CLOSED: "SUNA_MODAL_CLOSED",
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// Component Props
// ═══════════════════════════════════════════════════════════════════════════
interface SunaProfileSelectorProps extends InputProps {
    /**
     * The toolkit slug to filter profiles by (e.g., "gmail", "slack")
     * If provided, only shows profiles for this toolkit
     */
    toolkitSlug?: string;

    /**
     * Current external_profile_id value
     */
    selectedProfileId?: string;

    /**
     * Callback to update multiple template fields at once
     */
    onProfileChange?: (profileId: string, mcpUrl: string, toolkitSlug: string) => void;
}

interface ProfileOption {
    value: string;
    label: string;
    toolkit: string;
    toolkitSlug: string;
    iconUrl?: string;
    isDefault?: boolean;
    isConnected?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════════════════
export default function SunaProfileSelectorComponent({
    id,
    value,
    editNode,
    handleOnNewValue,
    disabled,
    nodeClass,
    nodeId,
    handleNodeClass,
    toolkitSlug,
    selectedProfileId,
    onProfileChange,
    helperText,
    ...baseInputProps
}: SunaProfileSelectorProps) {
    // ═══════════════════════════════════════════════════════════════════════════
    // State
    // ═══════════════════════════════════════════════════════════════════════════
    const [profiles, setProfiles] = useState<ProfileOption[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isFetchingMcpUrl, setIsFetchingMcpUrl] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isAvailable, setIsAvailable] = useState(false);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    // ═══════════════════════════════════════════════════════════════════════════
    // Check if Suna integration is available
    // ═══════════════════════════════════════════════════════════════════════════
    useEffect(() => {
        const iframeModeAvailable = isSunaIntegrationAvailable();
        const apiClientAvailable = sunaApiClient.isAvailable();
        const available = iframeModeAvailable && apiClientAvailable;

        console.log("[SunaProfileSelector] Availability check:", {
            iframeModeAvailable,
            apiClientAvailable,
            combined: available,
            baseUrl: sunaApiClient.getBaseUrl?.() || "(no getBaseUrl method)",
        });

        setIsAvailable(available);

        if (!available) {
            const reasons: string[] = [];
            if (!iframeModeAvailable) reasons.push("iframe mode not detected or no suna_token");
            if (!apiClientAvailable) reasons.push("VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL not set");

            const errorMsg = `Suna integration not available: ${reasons.join(", ")}`;
            console.warn("[SunaProfileSelector]", errorMsg);
            setError(errorMsg);
        }
    }, []);

    // ═══════════════════════════════════════════════════════════════════════════
    // Ref for loadProfiles to avoid stale closure in message listener
    // ═══════════════════════════════════════════════════════════════════════════
    const loadProfilesRef = useRef<((forceRefresh?: boolean) => Promise<void>) | null>(null);

    // ═══════════════════════════════════════════════════════════════════════════
    // Open Suna Profile Management Modal (via postMessage)
    // ═══════════════════════════════════════════════════════════════════════════
    const handleManageProfiles = useCallback(() => {
        if (!window.parent || window.parent === window) {
            console.warn("[SunaProfileSelector] No parent window found");
            return;
        }

        console.log("[SunaProfileSelector] Requesting parent to open profile modal", { toolkitSlug });

        // Send message to parent Suna window
        window.parent.postMessage(
            {
                type: SUNA_MESSAGE_TYPES.OPEN_PROFILE_MODAL,
                payload: {
                    toolkit: toolkitSlug || null,
                    source: "langflow-composio-component",
                },
            } as SunaMessage,
            "*" // In production, specify exact origin
        );
    }, [toolkitSlug]);

    // ═══════════════════════════════════════════════════════════════════════════
    // Load profiles from Suna
    // ═══════════════════════════════════════════════════════════════════════════
    const loadProfiles = useCallback(async (forceRefresh = false) => {
        if (!isAvailable) return;

        setIsLoading(true);
        setError(null);

        try {
            console.log("[SunaProfileSelector] Loading profiles...", { toolkitSlug });

            const response = await sunaApiClient.getComposioProfiles(forceRefresh);

            // Transform response into dropdown options
            const options: ProfileOption[] = [];

            for (const toolkit of response.toolkits) {
                // Filter by toolkit slug if provided
                if (toolkitSlug && toolkit.toolkit_slug !== toolkitSlug) {
                    continue;
                }

                for (const profile of toolkit.profiles) {
                    // Only include connected profiles
                    if (!profile.is_connected) continue;

                    options.push({
                        value: profile.profile_id,
                        label: profile.display_name || profile.profile_name,
                        toolkit: toolkit.toolkit_name,
                        toolkitSlug: toolkit.toolkit_slug,
                        iconUrl: toolkit.icon_url,
                        isDefault: profile.is_default,
                        isConnected: profile.is_connected,
                    });
                }
            }

            // Sort: default first, then alphabetically
            options.sort((a, b) => {
                if (a.isDefault && !b.isDefault) return -1;
                if (!a.isDefault && b.isDefault) return 1;
                return a.label.localeCompare(b.label);
            });

            console.log("[SunaProfileSelector] Loaded profiles:", options.length);
            setProfiles(options);
        } catch (err) {
            console.error("[SunaProfileSelector] Failed to load profiles:", err);
            setError(err instanceof Error ? err.message : "Failed to load profiles");
        } finally {
            setIsLoading(false);
        }
    }, [isAvailable, toolkitSlug]);

    // Keep ref updated with latest loadProfiles
    useEffect(() => {
        loadProfilesRef.current = loadProfiles;
    }, [loadProfiles]);

    // Load profiles on mount
    useEffect(() => {
        if (isAvailable) {
            loadProfiles();
        }
    }, [isAvailable, loadProfiles]);

    // ═══════════════════════════════════════════════════════════════════════════
    // PostMessage Bridge - Listen for messages from Suna parent
    // Uses ref to avoid stale closure while keeping effect stable
    // ═══════════════════════════════════════════════════════════════════════════
    useEffect(() => {
        if (!isInIframe()) {
            console.log("[SunaProfileSelector] Not in iframe, skipping message listener");
            return;
        }

        console.log("[SunaProfileSelector] Setting up postMessage listener for parent updates");

        const handleMessage = (event: MessageEvent) => {
            // Validate origin (in production, verify against known Suna origins)
            const message = event.data as SunaMessage;

            if (!message?.type) return;

            // Only handle Suna-specific messages
            if (!message.type.startsWith('SUNA_')) return;

            console.log("[SunaProfileSelector] Received message from parent:", message.type, message.payload);

            switch (message.type) {
                case SUNA_MESSAGE_TYPES.PROFILES_UPDATED:
                case SUNA_MESSAGE_TYPES.MODAL_CLOSED:
                    console.log("[SunaProfileSelector] Profile update signal - refreshing profiles...");
                    // Use ref to get latest loadProfiles function
                    if (loadProfilesRef.current) {
                        loadProfilesRef.current(true);
                    } else {
                        console.warn("[SunaProfileSelector] loadProfiles not yet available");
                    }
                    break;
            }
        };

        window.addEventListener("message", handleMessage);
        console.log("[SunaProfileSelector] postMessage listener registered");

        return () => {
            window.removeEventListener("message", handleMessage);
            console.log("[SunaProfileSelector] postMessage listener removed");
        };
    }, []); // Empty deps - uses ref for loadProfiles

    // ═══════════════════════════════════════════════════════════════════════════
    // Handle profile selection - updates multiple template fields
    // ═══════════════════════════════════════════════════════════════════════════
    const handleProfileSelect = useCallback(async (profileId: string) => {
        if (!nodeClass || !handleNodeClass) {
            console.error("[SunaProfileSelector] nodeClass or handleNodeClass not available");
            return;
        }

        setIsDropdownOpen(false);

        if (!profileId) {
            // Clear selection - update all related fields
            const updatedNode = { ...nodeClass };
            if (updatedNode.template) {
                if (updatedNode.template.suna_profile_selector) {
                    updatedNode.template.suna_profile_selector.value = "";
                }
                if (updatedNode.template.external_profile_id) {
                    updatedNode.template.external_profile_id.value = "";
                }
                if (updatedNode.template.external_mcp_url) {
                    updatedNode.template.external_mcp_url.value = "";
                }
                if (updatedNode.template.external_toolkit_slug) {
                    updatedNode.template.external_toolkit_slug.value = "";
                }
            }
            handleNodeClass(updatedNode);
            return;
        }

        const selectedProfile = profiles.find((p) => p.value === profileId);
        if (!selectedProfile) {
            console.error("[SunaProfileSelector] Profile not found:", profileId);
            return;
        }

        console.log("[SunaProfileSelector] Profile selected:", selectedProfile.label);

        // Update the dropdown value immediately
        handleOnNewValue({ value: profileId });

        // Fetch the MCP URL for this profile
        setIsFetchingMcpUrl(true);
        setError(null);

        try {
            const mcpResponse = await sunaApiClient.getComposioMcpUrl(profileId);

            console.log("[SunaProfileSelector] Got MCP URL for profile");

            // Update ALL related template fields using handleNodeClass
            const updatedNode = { ...nodeClass };
            if (updatedNode.template) {
                // Update suna_profile_selector value
                if (updatedNode.template.suna_profile_selector) {
                    updatedNode.template.suna_profile_selector.value = profileId;
                }
                // Store the profile ID
                if (updatedNode.template.external_profile_id) {
                    updatedNode.template.external_profile_id.value = profileId;
                }
                // Store the MCP URL (the key credential for execution)
                if (updatedNode.template.external_mcp_url) {
                    updatedNode.template.external_mcp_url.value = mcpResponse.mcp_url;
                }
                // Store the toolkit slug for filtering
                if (updatedNode.template.external_toolkit_slug) {
                    updatedNode.template.external_toolkit_slug.value = selectedProfile.toolkitSlug;
                }
            }

            // Apply all template updates at once
            handleNodeClass(updatedNode);

            console.log("[SunaProfileSelector] Updated template fields:", {
                suna_profile_selector: profileId,
                external_profile_id: profileId,
                external_mcp_url: "***hidden***",
                external_toolkit_slug: selectedProfile.toolkitSlug,
            });
        } catch (err) {
            console.error("[SunaProfileSelector] Failed to get MCP URL:", err);
            setError("Failed to get credentials for this profile");
        } finally {
            setIsFetchingMcpUrl(false);
        }
    }, [profiles, handleOnNewValue, nodeClass, handleNodeClass]);

    // ═══════════════════════════════════════════════════════════════════════════
    // Get current selection display
    // ═══════════════════════════════════════════════════════════════════════════
    const selectedOption = useMemo(() => {
        return profiles.find((p) => p.value === value);
    }, [profiles, value]);

    // ═══════════════════════════════════════════════════════════════════════════
    // Render - Premium UI
    // ═══════════════════════════════════════════════════════════════════════════

    // Not available state
    if (!isAvailable) {
        return (
            <div className="relative overflow-hidden rounded-xl border border-destructive/30 bg-destructive/5 p-3">
                <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10">
                        <AlertCircle className="h-4 w-4 text-destructive" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-destructive">Integration Unavailable</p>
                        <p className="text-xs text-destructive/70">
                            Connect via Suna Kortix to enable profiles
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Error state with profiles loaded
    if (error && profiles.length === 0) {
        return (
            <div className="relative overflow-hidden rounded-xl border border-destructive/30 bg-destructive/5 p-3">
                <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10">
                        <AlertCircle className="h-4 w-4 text-destructive" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-destructive">Failed to Load</p>
                        <p className="text-xs text-destructive/70 truncate">{error}</p>
                    </div>
                    <button
                        onClick={() => loadProfiles(true)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10 text-destructive transition-all hover:bg-destructive/20"
                        title="Retry"
                    >
                        <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex w-full flex-col gap-3">
            {/* Main Selection Row */}
            <div className="flex items-stretch gap-2">
                {/* Custom Dropdown */}
                <div className="relative flex-1">
                    <button
                        type="button"
                        onClick={() => !disabled && !isLoading && !isFetchingMcpUrl && setIsDropdownOpen(!isDropdownOpen)}
                        disabled={disabled || isLoading || isFetchingMcpUrl}
                        className={`
                            flex h-10 w-full items-center justify-between gap-2 rounded-xl border 
                            bg-background/80 px-3 text-sm transition-all duration-200 backdrop-blur-sm
                            ${isDropdownOpen
                                ? "border-primary/50 ring-2 ring-primary/20"
                                : "border-border/50 hover:border-border"
                            }
                            ${disabled || isLoading || isFetchingMcpUrl
                                ? "cursor-not-allowed opacity-50"
                                : "cursor-pointer hover:bg-accent/30"
                            }
                        `}
                    >
                        {/* Left side: Icon + Label */}
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                            {isLoading ? (
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            ) : selectedOption?.iconUrl ? (
                                <img
                                    src={selectedOption.iconUrl}
                                    //alt={selectedOption.toolkit}
                                    className="h-4 w-4 rounded object-contain"
                                />
                            ) : selectedOption ? (
                                <User className="h-4 w-4 text-primary" />
                            ) : (
                                <Zap className="h-4 w-4 text-muted-foreground" />
                            )}
                            <span className={`truncate ${selectedOption ? "text-foreground" : "text-muted-foreground"}`}>
                                {isLoading
                                    ? "Loading profiles..."
                                    : selectedOption
                                        ? selectedOption.label
                                        : "Select a profile..."
                                }
                            </span>
                            {selectedOption?.isDefault && (
                                <span className="flex items-center gap-0.5 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                                    <Sparkles className="h-2.5 w-2.5" />
                                    Default
                                </span>
                            )}
                        </div>

                        {/* Right side: Chevron */}
                        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${isDropdownOpen ? "rotate-180" : ""}`} />
                    </button>

                    {/* Dropdown Menu */}
                    {isDropdownOpen && (
                        <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-60 overflow-auto rounded-xl border border-border/50 bg-background/95 p-1 shadow-lg backdrop-blur-lg">
                            {/* Clear option */}
                            <button
                                type="button"
                                onClick={() => handleProfileSelect("")}
                                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent/50"
                            >
                                <span className="h-4 w-4" />
                                <span>Clear selection</span>
                            </button>

                            {/* Divider */}
                            {profiles.length > 0 && (
                                <div className="my-1 h-px bg-border/50" />
                            )}

                            {/* Profile options */}
                            {profiles.map((profile) => (
                                <button
                                    key={profile.value}
                                    type="button"
                                    onClick={() => handleProfileSelect(profile.value)}
                                    className={`
                                        flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors
                                        ${profile.value === value
                                            ? "bg-primary/10 text-primary"
                                            : "text-foreground hover:bg-accent/50"
                                        }
                                    `}
                                >
                                    {profile.iconUrl ? (
                                        <img
                                            src={profile.iconUrl}
                                            alt={profile.toolkit}
                                            className="h-4 w-4 rounded object-contain"
                                        />
                                    ) : (
                                        <User className="h-4 w-4" />
                                    )}
                                    <span className="flex-1 truncate text-left">{profile.label}</span>
                                    {!toolkitSlug && (
                                        <span className="text-xs text-muted-foreground">{profile.toolkit}</span>
                                    )}
                                    {profile.isDefault && (
                                        <Sparkles className="h-3 w-3 text-primary" />
                                    )}
                                    {profile.value === value && (
                                        <CheckCircle2 className="h-4 w-4 text-primary" />
                                    )}
                                </button>
                            ))}

                            {/* No profiles message */}
                            {profiles.length === 0 && !isLoading && (
                                <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                                    <p>No connected profiles</p>
                                    <p className="mt-1 text-xs">Click "Manage" to add one</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Click outside to close */}
                    {isDropdownOpen && (
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setIsDropdownOpen(false)}
                        />
                    )}
                </div>

                {/* Refresh Button */}
                <button
                    onClick={() => loadProfiles(true)}
                    disabled={isLoading}
                    className={`
                        flex h-10 w-10 items-center justify-center rounded-xl border border-border/50 
                        bg-background/80 text-muted-foreground backdrop-blur-sm transition-all duration-200
                        hover:border-border hover:bg-accent/30 hover:text-foreground
                        disabled:cursor-not-allowed disabled:opacity-50
                    `}
                    title="Refresh profiles"
                >
                    {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <RefreshCw className="h-4 w-4" />
                    )}
                </button>
            </div>

            {/* Status Indicators */}
            {isFetchingMcpUrl && (
                <div className="flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-xs text-primary">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Loading credentials...</span>
                </div>
            )}

            {error && profiles.length > 0 && (
                <div className="flex items-center gap-2 rounded-lg bg-destructive/5 px-3 py-2 text-xs text-destructive">
                    <AlertCircle className="h-3 w-3" />
                    <span>{error}</span>
                </div>
            )}

            {selectedOption && !isFetchingMcpUrl && !error && (
                <div className="flex items-center gap-2 rounded-lg bg-green-500/5 px-3 py-2 text-xs text-green-600 dark:text-green-400">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>
                        Connected as <span className="font-medium">{selectedOption.label}</span>
                        {selectedOption.isDefault && " (default)"}
                    </span>
                </div>
            )}

            {/* Helper text */}
            {helperText && !error && !selectedOption && (
                <p className="text-xs text-muted-foreground">{helperText}</p>
            )}

            {/* No profiles hint */}
            {!isLoading && profiles.length === 0 && !error && (
                <div className="rounded-lg border border-dashed border-border/50 bg-muted/30 p-3 text-center">
                    <p className="text-xs text-muted-foreground">
                        No connected profiles found.
                    </p>
                    <button
                        onClick={handleManageProfiles}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                        <Settings className="h-3 w-3" />
                        Connect {toolkitSlug || "an app"} in Suna
                    </button>
                </div>
            )}
        </div>
    );
}
