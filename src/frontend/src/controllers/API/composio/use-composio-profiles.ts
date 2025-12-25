import { useQuery } from "@tanstack/react-query";
import { composioKeys } from "./keys";
import { composioApi, ComposioProfile, ToolkitGroup } from "./utils";

export const useComposioProfiles = (params?: { toolkit_slug?: string; is_connected?: boolean }) => {
    return useQuery({
        queryKey: composioKeys.profiles.list(params),
        queryFn: () => composioApi.listProfiles(params),
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
};

export const useGroupedProfiles = () => {
    return useQuery({
        queryKey: composioKeys.profiles.grouped(),
        queryFn: () => composioApi.getGroupedProfiles(),
        staleTime: 5 * 60 * 1000,
    });
};

export const useComposioMcpUrl = (profileId: string, enabled = true) => {
    return useQuery({
        queryKey: composioKeys.profiles.mcpUrl(profileId),
        queryFn: () => composioApi.getMcpUrl(profileId),
        enabled: enabled && !!profileId,
        staleTime: 10 * 60 * 1000, // 10 minutes (URLs don't change often)
    });
};
