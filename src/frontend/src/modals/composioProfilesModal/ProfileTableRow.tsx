import React from "react";
import { Eye, Crown, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProfileTableRowProps } from "./types";
import { SelectableRow } from "./SelectableRow";

/**
 * Profile table row component
 * Displays a single Composio profile with actions (View MCP URL, Set Default, Delete)
 */
export function ProfileTableRow({
  profile,
  isSelected,
  onSelect,
  onDelete,
  onSetDefault,
}: ProfileTableRowProps) {
  const handleSelect = (item: typeof profile, selected: boolean) => {
    onSelect(item.id, selected);
  };

  return (
    <SelectableRow
      item={profile}
      isSelected={isSelected}
      onSelect={handleSelect}
      className="composio-profile-row"
    >
      <div className="flex flex-1 items-center justify-between gap-4 rounded-md border border-border bg-background px-4 py-3 hover:bg-muted/50 transition-colors">
        {/* Profile Info */}
        <div className="flex flex-1 items-center gap-4">
          {/* Toolkit Name */}
          <div className="min-w-[120px]">
            <span className="text-sm font-medium text-foreground capitalize">
              {profile.toolkit_slug.replace(/_/g, " ")}
            </span>
          </div>

          {/* Profile Name */}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm text-foreground">
                {profile.display_name || profile.profile_name}
              </span>
              {profile.is_default && (
                <div title="Default profile">
                  <Crown className="h-3 w-3 text-yellow-500" />
                </div>
              )}
            </div>
            {!profile.is_connected && (
              <span className="text-xs text-muted-foreground">Not connected</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              // This will be handled by parent component (McpUrlDialog)
              const event = new CustomEvent("viewMcpUrl", { detail: profile.id });
              window.dispatchEvent(event);
            }}
            className="h-8 gap-1 px-2"
            title="View MCP URL"
          >
            <Eye className="h-3 w-3" />
            View URL
          </Button>

          {!profile.is_default && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onSetDefault(profile.id)}
              className="h-8 gap-1 px-2"
              title="Set as default profile"
            >
              <Crown className="h-3 w-3" />
              Set Default
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(profile.id)}
            className="h-8 gap-1 px-2 text-destructive hover:text-destructive"
            title="Delete profile"
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </Button>
        </div>
      </div>
    </SelectableRow>
  );
}
