import React from "react";
import { GenericSelectableRowProps } from "./types";

/**
 * Generic selectable row wrapper with checkbox
 * Wraps any row content and adds selection checkbox functionality
 */
export function SelectableRow<T extends { id: string }>({
  item,
  isSelected,
  onSelect,
  children,
  className = "",
}: GenericSelectableRowProps<T>) {
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSelect(item, e.target.checked);
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <input
        type="checkbox"
        checked={isSelected}
        onChange={handleCheckboxChange}
        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2"
        aria-label={`Select item ${item.id}`}
      />
      {children}
    </div>
  );
}
