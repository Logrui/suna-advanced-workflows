import React from "react";
import { X, Trash2, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BulkActionsBarProps } from "./types";

/**
 * Bulk actions toolbar for selected items
 * Displays selected count and action buttons (delete, export, clear)
 */
export function BulkActionsBar({
  selectedCount,
  onClearSelection,
  onDelete,
  onExport,
}: BulkActionsBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center justify-between rounded-md border border-border bg-muted px-4 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">
          {selectedCount} {selectedCount === 1 ? "item" : "items"} selected
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearSelection}
          className="h-7 gap-1 px-2"
        >
          <X className="h-3 w-3" />
          Clear
        </Button>
      </div>

      <div className="flex items-center gap-2">
        {onExport && (
          <Button
            variant="outline"
            size="sm"
            onClick={onExport}
            className="h-7 gap-1 px-3"
          >
            <Download className="h-3 w-3" />
            Export
          </Button>
        )}
        {onDelete && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onDelete}
            className="h-7 gap-1 px-3"
          >
            <Trash2 className="h-3 w-3" />
            Delete
          </Button>
        )}
      </div>
    </div>
  );
}
