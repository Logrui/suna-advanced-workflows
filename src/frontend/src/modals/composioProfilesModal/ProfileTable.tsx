import React, { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProfileTableProps } from "./types";
import { ProfileTableRow } from "./ProfileTableRow";
import { BulkActionsBar } from "./BulkActionsBar";

/**
 * Main profile table component
 * Displays list of Composio profiles with selection and bulk actions
 */
export function ProfileTable({
  profiles,
  isLoading,
  onRefresh,
}: ProfileTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Selection handlers
  const handleSelect = (id: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(id);
      } else {
        newSet.delete(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(new Set(profiles.map((p) => p.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleClearSelection = () => {
    setSelectedIds(new Set());
  };

  const handleBulkDelete = () => {
    // Emit custom event for bulk delete
    const event = new CustomEvent("bulkDeleteProfiles", {
      detail: Array.from(selectedIds),
    });
    window.dispatchEvent(event);
    setSelectedIds(new Set());
  };

  const handleDelete = (id: string) => {
    // Emit custom event for single delete
    const event = new CustomEvent("deleteProfile", { detail: id });
    window.dispatchEvent(event);
    // Remove from selection if selected
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
  };

  const handleSetDefault = (id: string) => {
    // Emit custom event for set default
    const event = new CustomEvent("setDefaultProfile", { detail: id });
    window.dispatchEvent(event);
  };

  const allSelected = profiles.length > 0 && selectedIds.size === profiles.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < profiles.length;

  // Loading state
  if (isLoading) {
    return (
      <div className="composio-profile-table">
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading profiles...</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (profiles.length === 0) {
    return (
      <div className="composio-profile-table">
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="text-sm font-medium text-foreground">No profiles found</p>
            <p className="text-xs text-muted-foreground">
              Create a new profile to get started
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="composio-profile-table space-y-3">
      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectedIds.size}
        onClearSelection={handleClearSelection}
        onDelete={handleBulkDelete}
      />

      {/* Table Header */}
      <div className="flex items-center gap-3 border-b border-border px-4 pb-2">
        <input
          type="checkbox"
          checked={allSelected}
          ref={(input) => {
            if (input) {
              input.indeterminate = someSelected;
            }
          }}
          onChange={handleSelectAll}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2"
          aria-label="Select all profiles"
        />
        <div className="flex flex-1 items-center gap-4 px-4">
          <div className="min-w-[120px]">
            <span className="text-xs font-semibold uppercase text-muted-foreground">
              Toolkit
            </span>
          </div>
          <div className="flex-1">
            <span className="text-xs font-semibold uppercase text-muted-foreground">
              Profile Name
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase text-muted-foreground">
              Actions
            </span>
            <Button
              variant="ghost"
              size="iconSm"
              onClick={onRefresh}
              className="h-6 w-6"
              title="Refresh profiles"
            >
              <RefreshCw className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      {/* Table Rows */}
      <div className="space-y-2">
        {profiles.map((profile) => (
          <ProfileTableRow
            key={profile.id}
            profile={profile}
            isSelected={selectedIds.has(profile.id)}
            onSelect={handleSelect}
            onDelete={handleDelete}
            onSetDefault={handleSetDefault}
          />
        ))}
      </div>
    </div>
  );
}
