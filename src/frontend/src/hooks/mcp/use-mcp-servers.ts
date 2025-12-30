import { useQuery } from '@tanstack/react-query';
import { sunaApiClient } from '@/lib/suna-api-client';

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

export interface MCPServerInfo {
    toolkit_slug: string;
    toolkit_name: string;
    icon_url?: string;
    profile_count: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// Hooks
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Hook to fetch all available MCP servers (Composio toolkits) from Suna Kortix.
 * This returns the list of toolkits that have profiles configured.
 */
export const useMCPServers = (enabled: boolean = true) => {
    return useQuery({
        queryKey: ['mcp-servers'],
        queryFn: async (): Promise<MCPServerInfo[]> => {
            const response = await sunaApiClient.getComposioProfiles();
            return response.toolkits.map((toolkit) => ({
                toolkit_slug: toolkit.toolkit_slug,
                toolkit_name: toolkit.toolkit_name,
                icon_url: toolkit.icon_url,
                profile_count: toolkit.profiles.length,
            }));
        },
        enabled: enabled && sunaApiClient.isAvailable(),
        staleTime: 5 * 60 * 1000,
    });
};

/**
 * Hook to check if Suna MCP integration is available.
 */
export const useMCPServersAvailable = () => {
    return sunaApiClient.isAvailable();
};
