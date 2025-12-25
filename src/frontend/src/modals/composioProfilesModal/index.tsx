import React from "react";
import BaseModal from "../baseModal";
import { ComposioConnectionsSection } from "./ComposioConnectionsSection";

interface ComposioProfilesModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

/**
 * Modal wrapper for Composio Profile Management
 * - Provides modal container with header and footer
 * - Wraps ComposioConnectionsSection for profile management
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
      size="medium-h-full"
      className="composio-profiles-modal"
    >
      <BaseModal.Header description="Manage your Composio integration connections and OAuth profiles">
        <span className="font-semibold">Composio Connections</span>
      </BaseModal.Header>

      <BaseModal.Content>
        <ComposioConnectionsSection onClose={handleClose} />
      </BaseModal.Content>
    </BaseModal>
  );
}

export default ComposioProfilesModal;
