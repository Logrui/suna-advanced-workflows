import React, { useState, useMemo, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Search, Zap, X, ChevronDown, ChevronUp, Loader2, Server, Lock } from 'lucide-react';
import { useComposioCategories, useComposioToolkitsInfinite } from '@/hooks/composio/use-composio';
import { useComposioProfiles } from '@/hooks/composio/use-composio-profiles';
import { ComposioConnector } from './composio-connector';
import type { ComposioToolkit, ComposioProfile } from '@/hooks/composio/utils';
import { cn } from '@/utils/utils';
import { useQueryClient } from '@tanstack/react-query';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { CustomMCPDialog, type CustomMCPConfiguration } from '../mcp/custom-mcp-dialog';

const CATEGORY_EMOJIS: Record<string, string> = {
  'popular': '🔥',
  'productivity': '📊',
  'crm': '👥',
  'marketing': '📢',
  'analytics': '📈',
  'communication': '💬',
  'project-management': '📋',
  'scheduling': '📅',
};

interface ConnectedApp {
  toolkit: ComposioToolkit;
  profile: ComposioProfile;
}

interface ComposioRegistryProps {
  onToolsSelected?: (profileId: string, selectedTools: string[], appName: string, appSlug: string, appIconUrl?: string) => void;
  onAppSelected?: (app: ComposioToolkit) => void;
  mode?: 'full' | 'profile-only';
  onClose?: () => void;
  initialSelectedApp?: string | null;
  isBlocked?: boolean;
  onBlockedClick?: () => void;
}

const getConnectedApps = (
  profiles: ComposioProfile[],
  toolkits: ComposioToolkit[]
): ConnectedApp[] => {
  if (!profiles?.length || !toolkits?.length) return [];

  const connectedApps: ConnectedApp[] = [];
  const processedProfiles = new Set<string>();

  profiles.forEach(profile => {
    if (profile.is_connected && !processedProfiles.has(profile.profile_id)) {
      const toolkit = toolkits.find(t => t.slug === profile.toolkit_slug);
      if (toolkit) {
        connectedApps.push({
          toolkit,
          profile
        });
        processedProfiles.add(profile.profile_id);
      }
    }
  });

  return connectedApps;
};

const AppCardSkeleton = () => (
  <div className="border border-border/50 rounded-xl p-4">
    <div className="flex items-center gap-3 mb-3">
      <Skeleton className="w-10 h-10 rounded-lg" />
      <div className="flex-1">
        <Skeleton className="w-3/4 h-4 mb-2" />
        <Skeleton className="w-full h-3" />
      </div>
    </div>
    <div className="flex flex-wrap gap-1 mb-3">
      <Skeleton className="w-16 h-5" />
      <Skeleton className="w-20 h-5" />
    </div>
    <div className="flex justify-between items-center">
      <Skeleton className="w-24 h-6" />
      <Skeleton className="w-20 h-8" />
    </div>
  </div>
);

const ConnectedAppSkeleton = () => (
  <div className="border border-border/50 rounded-2xl p-4">
    <div className="flex items-start gap-3 mb-3">
      <Skeleton className="w-10 h-10 rounded-lg" />
      <div className="flex-1">
        <Skeleton className="w-3/4 h-4 mb-2" />
        <Skeleton className="w-full h-3" />
      </div>
      <Skeleton className="w-8 h-8 rounded" />
    </div>
    <div className="flex justify-between items-center">
      <Skeleton className="w-32 h-4" />
    </div>
  </div>
);

const ConnectedAppCard = ({
  connectedApp,
  onConfigure
}: {
  connectedApp: ConnectedApp;
  onConfigure: (app: ComposioToolkit, profile: ComposioProfile) => void;
}) => {
  const { toolkit, profile } = connectedApp;

  return (
    <div
      role="button"
      tabIndex={0}
      className="group border bg-card rounded-2xl p-4 transition-all duration-200 cursor-pointer hover:border-primary/50"
      onClick={() => onConfigure(toolkit, profile)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onConfigure(toolkit, profile);
        }
      }}
    >
      <div className="flex items-start gap-3 mb-3">
        {toolkit.logo ? (
          <img src={toolkit.logo} alt={toolkit.name} className="w-10 h-10 rounded-xl object-cover p-2 bg-muted border" />
        ) : (
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <span className="text-primary text-sm font-medium">{toolkit.name.charAt(0)}</span>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm leading-tight truncate mb-1">{toolkit.name}</h3>
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            Connected as "{profile.profile_name}"
          </p>
        </div>
      </div>
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          Active
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-xs hover:bg-primary/5 hover:text-primary z-10"
          onClick={(e) => {
            e.stopPropagation();
            onConfigure(toolkit, profile);
          }}
        >
          Manage Tools
        </Button>
      </div>
    </div>
  );
};

const AppCard = ({ app, profiles, onConnect, onConfigure, isBlocked, onBlockedClick }: {
  app: ComposioToolkit;
  profiles: ComposioProfile[];
  onConnect: () => void;
  onConfigure: (profile: ComposioProfile) => void;
  isBlocked?: boolean;
  onBlockedClick?: () => void;
}) => {
  const connectedProfiles = profiles.filter(p => p.is_connected);

  const getStatusInfo = () => {
    if (isBlocked) {
      return { text: 'Upgrade to connect', color: 'text-primary' };
    }
    return connectedProfiles.length > 0
      ? { text: `${connectedProfiles.length} profile${connectedProfiles.length !== 1 ? 's' : ''}`, color: 'text-green-600 dark:text-green-400' }
      : { text: '', color: 'text-muted-foreground' };
  };

  const status = getStatusInfo();

  const handleClick = () => {
    if (isBlocked && onBlockedClick) {
      onBlockedClick();
      return;
    }
    if (connectedProfiles.length > 0) {
      onConfigure(connectedProfiles[0]);
    } else {
      onConnect();
    }
  };

  return (
    <Card
      role="button"
      tabIndex={isBlocked ? -1 : 0}
      className={cn(
        "p-4 flex flex-col transition-all duration-200 gap-1 relative",
        isBlocked ? "hover:bg-muted cursor-pointer hover:border-primary/50" : "hover:bg-muted cursor-pointer"
      )}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (!isBlocked && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {status.text && (
        <div className={cn("absolute top-4 right-4 text-xs", status.color)}>
          {status.text}
        </div>
      )}

      <div className="w-[40px] h-[40px] rounded-xl border border-border bg-background flex items-center justify-center mb-4 relative">
        {app.logo ? (
          <img src={app.logo} alt={app.name} className="w-5 h-5 object-contain" />
        ) : (
          <span className="text-foreground text-sm font-medium">{app.name.charAt(0)}</span>
        )}
        {isBlocked && (
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
            <Lock className="h-2.5 w-2.5 text-primary-foreground" strokeWidth={2.5} />
          </div>
        )}
      </div>

      <h3 className="font-medium text-lg leading-tight">{app.name}</h3>

      <p className="text-sm text-muted-foreground flex-1 line-clamp-2 leading-snug mb-4 mt-1">
        {app.description || `Builds user interfaces and interactive web pages.`}
      </p>

      <Button
        variant={isBlocked ? "outline" : "default"}
        className={cn("w-full", isBlocked && "border-primary text-primary hover:bg-primary hover:text-primary-foreground")}
        disabled={isBlocked}
      >
        {isBlocked ? (
          <>
            <Lock className="h-3.5 w-3.5 mr-2" />
            Upgrade
          </>
        ) : (
          <>
            <span className="text-lg font-light mr-2">+</span> Add
          </>
        )}
      </Button>
    </Card>
  );
};

export const ComposioRegistry: React.FC<ComposioRegistryProps> = ({
  onToolsSelected,
  onAppSelected,
  mode = 'full',
  onClose,
  initialSelectedApp,
  isBlocked = false,
  onBlockedClick,
}) => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedApp, setSelectedApp] = useState<ComposioToolkit | null>(null);
  const [showConnector, setShowConnector] = useState(false);
  const [showConnectedApps, setShowConnectedApps] = useState(true);
  const [showCustomMCPDialog, setShowCustomMCPDialog] = useState(false);

  const queryClient = useQueryClient();

  const { data: categoriesData } = useComposioCategories();
  const {
    data: toolkitsInfiniteData,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  } = useComposioToolkitsInfinite(search, selectedCategory);

  const { data: profiles, isLoading: isLoadingProfiles } = useComposioProfiles();

  const allToolkits = useMemo(() => {
    if (!toolkitsInfiniteData?.pages) return [];
    return toolkitsInfiniteData.pages.flatMap(page => page.toolkits || []);
  }, [toolkitsInfiniteData]);

  const profilesByToolkit = useMemo(() => {
    const grouped: Record<string, ComposioProfile[]> = {};
    profiles?.forEach(profile => {
      if (profile.is_connected) {
        if (!grouped[profile.toolkit_slug]) {
          grouped[profile.toolkit_slug] = [];
        }
        grouped[profile.toolkit_slug].push(profile);
      }
    });
    return grouped;
  }, [profiles]);

  const connectedApps = useMemo(() => {
    return getConnectedApps(profiles || [], allToolkits);
  }, [profiles, allToolkits]);

  // Handle initial app selection
  useEffect(() => {
    if (initialSelectedApp && allToolkits.length > 0 && !selectedApp) {
      const appToSelect = allToolkits.find(
        toolkit => toolkit.slug?.toLowerCase() === initialSelectedApp.toLowerCase()
      );
      if (appToSelect) {
        setSelectedApp(appToSelect);
        setShowConnector(true);
        setShowConnectedApps(false);
      }
    }
  }, [initialSelectedApp, allToolkits, selectedApp]);

  const handleConnect = (app: ComposioToolkit) => {
    setSelectedApp(app);
    setShowConnector(true);
  };

  const handleConfigure = (app: ComposioToolkit, profile: ComposioProfile) => {
    // Tools Manager temporarily disabled or implementation pending
    // console.log("Tools configuration for:", profile.profile_name);
    // setSelectedApp(app);
    // setToolsManagerProfile(profile);
  };

  const handleConnectionComplete = (profileId: string, appName: string, appSlug: string) => {
    setShowConnector(false);
    queryClient.invalidateQueries({ queryKey: ['composio', 'profiles'] });

    if (onToolsSelected) {
      onToolsSelected(profileId, [], appName, appSlug, selectedApp?.logo);
    }
  };

  const handleCustomMCPSave = (config: CustomMCPConfiguration): void => {
    // For now, these are not persisted to an agent, effectively purely local/session based or would need a different persistence backend
    console.log("Custom MCP Config:", config);
  };

  const categories = categoriesData?.categories || [];

  return (
    <div className="h-full w-full overflow-hidden flex">
      <div className="flex-1 h-full overflow-hidden">
        <div className="h-full flex flex-col">
          {/* Header Area */}
          <div className="flex-shrink-0 border-b p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1 min-w-0 pr-4">
                <h2 className="text-xl font-semibold">
                  App Integrations
                </h2>
                <p className="text-sm text-muted-foreground">
                  Manage your connections and profiles for third-party applications.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search apps..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10 h-10"
                  />
                </div>
                {/* Custom MCP potentially re-enabled if valid for this context */}
                <Button
                  variant="outline"
                  onClick={() => setShowCustomMCPDialog(true)}
                  className="flex items-center gap-2 whitespace-nowrap h-10"
                >
                  <Server className="h-4 w-4" />
                  Add Custom MCP
                </Button>
              </div>

              {selectedCategory && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Filtered by:</span>
                  <Badge variant="outline" className="gap-1 bg-muted-foreground/20 text-muted-foreground">
                    <span>{CATEGORY_EMOJIS[selectedCategory] || '📁'}</span>
                    <span>{categories.find(c => c.id === selectedCategory)?.name}</span>
                    <button
                      onClick={() => setSelectedCategory('')}
                      className="ml-1 hover:bg-muted rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="p-6 space-y-6">
                <Collapsible open={showConnectedApps} onOpenChange={setShowConnectedApps}>
                  <CollapsibleTrigger asChild>
                    <div className="w-full hover:underline flex items-center justify-between p-0 h-auto">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-medium">Active Connections</h3>
                        {isLoadingProfiles ? (
                          <Skeleton className="w-6 h-5 rounded ml-2" />
                        ) : connectedApps.length > 0 && (
                          <Badge variant="outline" className="ml-2">
                            {connectedApps.length}
                          </Badge>
                        )}
                      </div>
                      {showConnectedApps ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-4">
                    {isLoadingProfiles ? (
                      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {Array.from({ length: 3 }).map((_, i) => (
                          <ConnectedAppSkeleton key={i} />
                        ))}
                      </div>
                    ) : connectedApps.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4 mx-auto">
                          <Zap className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h4 className="text-sm font-medium mb-2">No active connections</h4>
                        <p className="text-xs">Connect apps below to use them in your workflows.</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-4 gap-4">
                        {connectedApps.map((connectedApp) => (
                          <ConnectedAppCard
                            key={connectedApp.profile.profile_id}
                            connectedApp={connectedApp}
                            onConfigure={handleConfigure}
                          />
                        ))}
                      </div>
                    )}
                  </CollapsibleContent>
                </Collapsible>

                <div>
                  <h3 className="text-lg font-medium mb-4">
                    Browse Apps
                  </h3>

                  {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      {Array.from({ length: 12 }).map((_, i) => (
                        <AppCardSkeleton key={i} />
                      ))}
                    </div>
                  ) : allToolkits?.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                        <Search className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <h3 className="text-lg font-medium mb-2">No apps found</h3>
                      <p className="text-muted-foreground">
                        {search ? `No apps match "${search}"` : 'No apps available'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {allToolkits?.map((app) => (
                          <AppCard
                            key={app.slug}
                            app={app}
                            profiles={profilesByToolkit[app.slug] || []}
                            onConnect={() => handleConnect(app)}
                            onConfigure={(profile) => handleConfigure(app, profile)}
                            isBlocked={isBlocked}
                            onBlockedClick={onBlockedClick}
                          />
                        ))}
                      </div>
                      {hasNextPage && (
                        <div className="flex justify-center pt-4">
                          <Button
                            variant="outline"
                            onClick={() => fetchNextPage()}
                            disabled={isFetchingNextPage}

                          >
                            {isFetchingNextPage ? (
                              <>
                                <Loader2 className="animate-spin h-4 w-4 " />
                                Loading more...
                              </>
                            ) : (
                              'Load More Apps'
                            )}
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
      {selectedApp && (
        <ComposioConnector
          app={selectedApp}
          agentId={undefined} // No agent context needed
          open={showConnector}
          onOpenChange={setShowConnector}
          onComplete={handleConnectionComplete}
          mode={mode}
        />
      )}

      <CustomMCPDialog
        open={showCustomMCPDialog}
        onOpenChange={setShowCustomMCPDialog}
        onSave={handleCustomMCPSave}
      />
    </div>
  );
};