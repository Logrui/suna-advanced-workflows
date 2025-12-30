import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { sunaApiClient, type ComposioProfileSummary, type ComposioToolkitGroup } from '@/lib/suna-api-client';

// Re-export types for external use
export type { ComposioProfileSummary, ComposioToolkitGroup };

/**
 * Hook to fetch all Composio profiles from Suna Kortix.
 * Returns profiles grouped by toolkit.
 */
export function useCredentialProfiles() {
    return useQuery({
        queryKey: ['composio-profiles', 'all'],
        queryFn: async () => {
            const response = await sunaApiClient.getComposioProfiles();
            return response.toolkits;
        },
        enabled: sunaApiClient.isAvailable(),
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook to fetch profiles for a specific toolkit/app.
 * @param toolkitSlug - The toolkit slug (e.g., "gmail", "slack")
 */
export function useCredentialProfilesForMcp(toolkitSlug: string | null) {
    return useQuery({
        queryKey: ['composio-profiles', toolkitSlug],
        queryFn: () => toolkitSlug ? sunaApiClient.getProfilesForToolkit(toolkitSlug) : Promise.resolve([]),
        enabled: !!toolkitSlug && sunaApiClient.isAvailable(),
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook to fetch the MCP URL for a specific profile.
 * @param profileId - The profile ID to get the MCP URL for
 */
export function useCredentialProfileMcpUrl(profileId: string | null) {
    return useQuery({
        queryKey: ['composio-profile-mcp-url', profileId],
        queryFn: () => profileId ? sunaApiClient.getComposioMcpUrl(profileId) : Promise.resolve(null),
        enabled: !!profileId && sunaApiClient.isAvailable(),
        staleTime: 0, // MCP URLs should always be fresh
        gcTime: 0,
    });
}

/**
 * Hook to get all profiles as a flat list (useful for dropdowns).
 */
export function useCredentialProfilesFlat() {
    return useQuery({
        queryKey: ['composio-profiles', 'flat'],
        queryFn: () => sunaApiClient.getAllProfilesFlat(),
        enabled: sunaApiClient.isAvailable(),
        staleTime: 5 * 60 * 1000,
    });
}

/**
 * Hook to invalidate the profiles cache and force a refresh.
 */
export function useRefreshCredentialProfiles() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            sunaApiClient.clearCache();
            await sunaApiClient.getComposioProfiles(true);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['composio-profiles'] });
            toast.success('Profiles refreshed');
        },
        onError: (error: Error) => {
            toast.error(`Failed to refresh profiles: ${error.message}`);
        },
    });
}

/**
 * Get the default profile for a toolkit.
 * @param toolkitSlug - The toolkit slug
 */
export function useGetDefaultProfile(toolkitSlug: string | null) {
    const { data: profiles } = useCredentialProfilesForMcp(toolkitSlug);
    return profiles?.find(profile => profile.is_default) || profiles?.[0] || null;
}

/**
 * Check if a toolkit has any profiles.
 * @param toolkitSlug - The toolkit slug
 */
export function useHasCredentialProfiles(toolkitSlug: string | null) {
    const { data: profiles, isLoading } = useCredentialProfilesForMcp(toolkitSlug);
    return {
        hasProfiles: (profiles?.length || 0) > 0,
        profileCount: profiles?.length || 0,
        isLoading,
    };
}

/**
 * Check if Suna API integration is available.
 */
export function useSunaApiAvailable() {
    return sunaApiClient.isAvailable();
}
