import { AlertCircle } from "lucide-react";
import React from "react";
import { Button } from "@/components/ui/button";
import BaseModal from "../baseModal";

interface DeleteConfirmationDialogProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  profileCount: number;
  loading?: boolean;
}

export default function DeleteConfirmationDialog({
  open,
  onConfirm,
  onCancel,
  profileCount,
  loading = false,
}: DeleteConfirmationDialogProps): JSX.Element {
  return (
    <BaseModal
      open={open}
      setOpen={(isOpen) => {
        if (!isOpen) {
          onCancel();
        }
      }}
      size="notice"
      className="composio-delete-dialog"
    >
      <BaseModal.Header
        description={`Are you sure you want to delete ${profileCount} profile${profileCount > 1 ? "s" : ""}? This action cannot be undone.`}
      >
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <span>Delete Confirmation</span>
        </div>
      </BaseModal.Header>

      <BaseModal.Content className="flex-none">
        <div className="flex items-center gap-3 rounded-md border border-destructive/20 bg-destructive/5 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-destructive" />
          <p className="text-sm text-muted-foreground">
            Deleting Composio profiles will remove all associated connections and configurations.
            Any workflows using these profiles may stop working.
          </p>
        </div>
      </BaseModal.Content>

      <BaseModal.Footer>
        <div className="flex w-full items-center justify-end gap-3">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={loading}
            data-testid="delete-dialog-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            loading={loading}
            disabled={loading}
            data-testid="delete-dialog-confirm"
          >
            Delete
          </Button>
        </div>
      </BaseModal.Footer>
    </BaseModal>
  );
}
