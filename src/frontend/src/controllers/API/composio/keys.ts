export const composioKeys = {
    all: ['composio'] as const,

    profiles: {
        all: () => [...composioKeys.all, 'profiles'] as const,
        list: (params?: { toolkit_slug?: string; is_connected?: boolean }) =>
            [...composioKeys.profiles.all(), 'list', params] as const,
        grouped: () => [...composioKeys.profiles.all(), 'grouped'] as const,
        detail: (id: string) => [...composioKeys.profiles.all(), 'detail', id] as const,
        mcpUrl: (id: string) => [...composioKeys.profiles.all(), 'mcp-url', id] as const,
        checkName: (toolkit: string, name: string) =>
            [...composioKeys.profiles.all(), 'check-name', toolkit, name] as const,
    },

    toolkits: {
        all: () => [...composioKeys.all, 'toolkits'] as const,
        icon: (slug: string) => [...composioKeys.toolkits.all(), 'icon', slug] as const,
    },
};
