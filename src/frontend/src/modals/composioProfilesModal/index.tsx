import React from "react";
import BaseModal from "../baseModal";
import { ComposioRegistry } from "../composio/composio-registry";

interface ComposioProfilesModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

/**
 * Modal wrapper for Composio Profile Management
 * - Provides modal container with header and footer
 * - Wraps ComposioRegistry for profile management
 * - Handles modal open/close state
 */
export function ComposioProfilesModal({
  open,
  setOpen,
}: ComposioProfilesModalProps): JSX.Element {
  const handleClose = () => {
    setOpen(false);
  };

  return (
    <BaseModal
      open={open}
      setOpen={setOpen}
      size="x-large"
      className="composio-profiles-modal"
    >
      <BaseModal.Header description="Manage your Composio integration connections and OAuth profiles">
        <span className="font-semibold">App Integrations</span>
      </BaseModal.Header>

      <BaseModal.Content className="p-0 overflow-hidden h-full">
        <ComposioRegistry
          mode="full"
          onClose={handleClose}
        />
      </BaseModal.Content>
    </BaseModal>
  );
}

export default ComposioProfilesModal;
