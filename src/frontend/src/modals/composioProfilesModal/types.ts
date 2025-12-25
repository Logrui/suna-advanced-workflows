import { ComposioProfile } from "@/controllers/API/composio";

export interface ProfileTableProps {
    profiles: ComposioProfile[];
    isLoading: boolean;
    onRefresh: () => void;
}

export interface ProfileTableRowProps {
    profile: ComposioProfile;
    isSelected: boolean;
    onSelect: (id: string, selected: boolean) => void;
    onDelete: (id: string) => void;
    onSetDefault: (id: string) => void;
}

export interface GenericSelectableRowProps<T> {
    item: T;
    isSelected: boolean;
    onSelect: (item: T, selected: boolean) => void;
    children: React.ReactNode;
    className?: string;
}

export interface BulkActionsBarProps {
    selectedCount: number;
    onClearSelection: () => void;
    onDelete?: () => void;
    onExport?: () => void;
}
