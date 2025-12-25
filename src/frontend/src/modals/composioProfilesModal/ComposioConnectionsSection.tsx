import { Plus, Search } from "lucide-react";
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import useAlertStore from "@/stores/alertStore";
import {
  useGroupedProfiles,
  useDeleteProfile,
  useBulkDeleteProfiles,
  useSetDefaultProfile,
  useComposioMcpUrl,
  type ComposioProfile,
} from "@/controllers/API/composio";
import { ProfileTable } from "./ProfileTable";
import DeleteConfirmationDialog from "./DeleteConfirmationDialog";
import McpUrlDialog from "./McpUrlDialog";
import ComposioConnector from "./ComposioConnector";

interface ComposioConnectionsSectionProps {
  onClose?: () => void;
}

/**
 * Main section for managing Composio profiles
 * - Displays profiles grouped by toolkit
 * - Handles single and bulk deletion
 * - Manages default profile setting
 * - Shows MCP URL dialog
 * - Opens OAuth connector for new connections
 */
export function ComposioConnectionsSection({
  onClose,
}: ComposioConnectionsSectionProps): JSX.Element {
  // =========================================================================
  // State Management
  // =========================================================================
  const [searchQuery, setSearchQuery] = useState("");
  const [showConnector, setShowConnector] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDeleteIds, setPendingDeleteIds] = useState<string[]>([]);
  const [mcpDialogOpen, setMcpDialogOpen] = useState(false);
  const [selectedProfileForMcp, setSelectedProfileForMcp] = useState<
    ComposioProfile | undefined
  >();

  // =========================================================================
  // API Hooks
  // =========================================================================
  const {
    data: groupedData,
    isLoading,
    refetch,
  } = useGroupedProfiles();

  // Debug logging
  React.useEffect(() => {
    console.log("[ComposioConnectionsSection] groupedData:", groupedData);
    console.log("[ComposioConnectionsSection] isLoading:", isLoading);
  }, [groupedData, isLoading]);

  const deleteProfileMutation = useDeleteProfile();
  const bulkDeleteMutation = useBulkDeleteProfiles();
  const setDefaultMutation = useSetDefaultProfile();

  const {
    data: mcpUrlData,
    isLoading: mcpUrlLoading,
  } = useComposioMcpUrl(
    selectedProfileForMcp?.id || "",
    mcpDialogOpen && !!selectedProfileForMcp
  );

  // =========================================================================
  // Alert Store
  // =========================================================================
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  // =========================================================================
  // Computed Data
  // =========================================================================

  // Flatten grouped profiles into a single array
  const allProfiles: ComposioProfile[] = React.useMemo(() => {
    if (!groupedData) {
      console.log("[ComposioConnectionsSection] groupedData is null/undefined");
      return [];
    }
    const profiles = groupedData.flatMap((group) => group.profiles);
    console.log("[ComposioConnectionsSection] Flattened profiles:", profiles.length, profiles);
    return profiles;
  }, [groupedData]);

  // Filter profiles by search query
  const filteredProfiles = React.useMemo(() => {
    if (!searchQuery.trim()) return allProfiles;

    const query = searchQuery.toLowerCase();
    return allProfiles.filter(
      (profile) =>
        profile.profile_name.toLowerCase().includes(query) ||
        profile.toolkit_slug.toLowerCase().includes(query) ||
        (profile.display_name &&
          profile.display_name.toLowerCase().includes(query))
    );
  }, [allProfiles, searchQuery]);

  // =========================================================================
  // Event Handlers - Window Events from ProfileTable
  // =========================================================================

  useEffect(() => {
    const handleDeleteProfile = (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      const profileId = customEvent.detail;
      setPendingDeleteIds([profileId]);
      setDeleteDialogOpen(true);
    };

    const handleBulkDelete = (event: Event) => {
      const customEvent = event as CustomEvent<string[]>;
      const profileIds = customEvent.detail;
      setPendingDeleteIds(profileIds);
      setDeleteDialogOpen(true);
    };

    const handleSetDefault = async (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      const profileId = customEvent.detail;

      try {
        await setDefaultMutation.mutateAsync(profileId);
        setSuccessData({ title: "Default profile updated successfully" });
      } catch (error) {
        const errorMsg =
          error instanceof Error ? error.message : "Failed to set default profile";
        setErrorData({
          title: "Failed to set default profile",
          list: [errorMsg],
        });
      }
    };

    const handleViewMcpUrl = (event: Event) => {
      const customEvent = event as CustomEvent<string>;
      const profileId = customEvent.detail;

      // Find the profile
      const profile = allProfiles.find((p) => p.id === profileId);
      if (profile) {
        setSelectedProfileForMcp(profile);
        setMcpDialogOpen(true);
      }
    };

    // Register event listeners
    window.addEventListener("deleteProfile", handleDeleteProfile);
    window.addEventListener("bulkDeleteProfiles", handleBulkDelete);
    window.addEventListener("setDefaultProfile", handleSetDefault);
    window.addEventListener("viewMcpUrl", handleViewMcpUrl);

    // Cleanup
    return () => {
      window.removeEventListener("deleteProfile", handleDeleteProfile);
      window.removeEventListener("bulkDeleteProfiles", handleBulkDelete);
      window.removeEventListener("setDefaultProfile", handleSetDefault);
      window.removeEventListener("viewMcpUrl", handleViewMcpUrl);
    };
  }, [
    allProfiles,
    setDefaultMutation,
    setSuccessData,
    setErrorData,
  ]);

  // =========================================================================
  // Deletion Handlers
  // =========================================================================

  const handleConfirmDelete = async () => {
    try {
      if (pendingDeleteIds.length === 1) {
        // Single delete
        await deleteProfileMutation.mutateAsync(pendingDeleteIds[0]);
        setSuccessData({ title: "Profile deleted successfully" });
      } else {
        // Bulk delete
        const result = await bulkDeleteMutation.mutateAsync(pendingDeleteIds);
        setSuccessData({
          title: `Deleted ${result.deleted_count} profile${result.deleted_count > 1 ? "s" : ""}`,
        });

        if (result.failed_ids && result.failed_ids.length > 0) {
          setErrorData({
            title: `Failed to delete ${result.failed_ids.length} profile(s)`,
            list: result.failed_ids.map((id) => `Profile ID: ${id}`),
          });
        }
      }

      // Refetch to update the list
      refetch();
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : "Failed to delete profile(s)";
      setErrorData({
        title: "Deletion failed",
        list: [errorMsg],
      });
    } finally {
      setDeleteDialogOpen(false);
      setPendingDeleteIds([]);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setPendingDeleteIds([]);
  };

  // =========================================================================
  // Connection Success Handler
  // =========================================================================

  const handleConnectionSuccess = () => {
    setShowConnector(false);
    refetch();
  };

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <div className="composio-connections-section flex h-full flex-col space-y-4">
      {/* Header Section */}
      <div className="flex items-center justify-between gap-4">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search profiles or toolkits..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-input bg-background py-2 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          />
        </div>

        {/* Add Connection Button */}
        <Button
          onClick={() => setShowConnector(true)}
          className="flex items-center gap-2"
          data-testid="add-connection-button"
        >
          <Plus className="h-4 w-4" />
          Add Connection
        </Button>
      </div>

      {/* Profile Table */}
      <div className="flex-1 overflow-auto">
        <ProfileTable
          profiles={filteredProfiles}
          isLoading={isLoading}
          onRefresh={refetch}
        />
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={deleteDialogOpen}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
        profileCount={pendingDeleteIds.length}
        loading={
          deleteProfileMutation.isPending || bulkDeleteMutation.isPending
        }
      />

      {/* MCP URL Dialog */}
      {selectedProfileForMcp && (
        <McpUrlDialog
          open={mcpDialogOpen}
          onClose={() => {
            setMcpDialogOpen(false);
            setSelectedProfileForMcp(undefined);
          }}
          profileName={selectedProfileForMcp.profile_name}
          mcpUrl={mcpUrlData?.mcp_url || ""}
        />
      )}

      {/* OAuth Connector Modal */}
      <ComposioConnector
        open={showConnector}
        onClose={() => setShowConnector(false)}
        onSuccess={handleConnectionSuccess}
      />
    </div>
  );
}

export default ComposioConnectionsSection;
