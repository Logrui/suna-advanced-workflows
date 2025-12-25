import { api } from "@/controllers/API/api";

// Types
export interface ComposioProfile {
    id: string;
    user_id: string;
    toolkit_slug: string;
    profile_name: string;
    display_name: string | null;
    connected_account_id: string | null;
    is_connected: boolean;
    is_active: boolean;
    is_default: boolean;
    created_at: string;
    updated_at: string | null;
    last_used_at: string | null;
}

export interface ToolkitGroup {
    toolkit_slug: string;
    toolkit_name: string;
    icon_url: string | null;
    profiles: ComposioProfile[];
}

export interface CreateProfileRequest {
    toolkit_slug: string;
    profile_name: string;
    display_name?: string;
    mcp_url: string;
    connected_account_id: string;
    composio_user_id: string;
    is_default?: boolean;
    is_connected?: boolean;
    redirect_url?: string;
}

export interface CreateProfileResponse {
    success: boolean;
    profile_id: string;
    profile_name: string;
    toolkit_slug: string;
    redirect_url?: string;
    message?: string;
}

// API Client
export const composioApi = {
    // Profiles
    async listProfiles(params?: { toolkit_slug?: string; is_connected?: boolean }): Promise<ComposioProfile[]> {
        const queryParams = new URLSearchParams();
        if (params?.toolkit_slug) queryParams.append("toolkit_slug", params.toolkit_slug);
        if (params?.is_connected !== undefined) queryParams.append("is_connected", String(params.is_connected));

        const response = await api.get(`/api/v1/composio-profiles?${queryParams}`);
        return response.data.profiles;
    },

    async getGroupedProfiles(): Promise<ToolkitGroup[]> {
        const response = await api.get("/api/v1/composio-profiles/grouped");
        return response.data.toolkits;
    },

    async createProfile(request: CreateProfileRequest): Promise<CreateProfileResponse> {
        const response = await api.post("/api/v1/composio-profiles", request);
        return response.data;
    },

    async deleteProfile(profileId: string): Promise<{ success: boolean; message: string }> {
        const response = await api.delete(`/api/v1/composio-profiles/${profileId}`);
        return response.data;
    },

    async bulkDeleteProfiles(profileIds: string[]): Promise<{ deleted_count: number; failed_ids: string[] }> {
        const response = await api.post("/api/v1/composio-profiles/bulk-delete", { profile_ids: profileIds });
        return response.data;
    },

    async setDefaultProfile(profileId: string): Promise<{ success: boolean; message: string }> {
        const response = await api.post(`/api/v1/composio-profiles/${profileId}/set-default`);
        return response.data;
    },

    async markConnected(profileId: string): Promise<ComposioProfile> {
        const response = await api.post(`/api/v1/composio-profiles/${profileId}/mark-connected`);
        return response.data;
    },

    async getMcpUrl(profileId: string): Promise<{ mcp_url: string; toolkit_slug: string }> {
        const response = await api.get(`/api/v1/composio-profiles/${profileId}/mcp-url`);
        return response.data;
    },

    async checkNameAvailability(toolkitSlug: string, profileName: string): Promise<{
        available: boolean;
        message: string;
        suggestions: string[];
    }> {
        const params = new URLSearchParams({ toolkit_slug: toolkitSlug, profile_name: profileName });
        const response = await api.get(`/api/v1/composio-profiles/check-name?${params}`);
        return response.data;
    },
};
