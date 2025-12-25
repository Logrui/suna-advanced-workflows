import { useState } from "react";
import ComposioProfilesModal from "@/modals/composioProfilesModal";
import { Button } from "@/components/ui/button";
import IconComponent from "../../../../common/genericIconComponent";
import type { InputProps } from "../../types";

/**
 * ComposioProfilesModalTrigger
 *
 * Opens the Composio Profiles management modal when clicked.
 * Used as a field_type="composio_profiles_modal" in Python components.
 */
export default function ComposioProfilesModalTrigger({
  value,
  disabled = false,
  id = "",
  handleOnNewValue,
}: InputProps<string>): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpenModal = () => {
    setIsOpen(true);
  };

  const handleCloseModal = () => {
    setIsOpen(false);
  };

  const handleSuccess = () => {
    // Notify parent component of successful connection
    if (handleOnNewValue) {
      handleOnNewValue({ value: "profiles_updated" });
    }
  };

  return (
    <>
      <Button
        data-testid={`composio-profiles-trigger-${id}`}
        onClick={handleOpenModal}
        disabled={disabled}
        variant="default"
        className="w-full justify-between"
      >
        <span className="flex items-center gap-2">
          <IconComponent name="Settings" className="h-4 w-4" />
          Manage Composio Profiles
        </span>
        <IconComponent name="ChevronRight" className="h-4 w-4" />
      </Button>

      {/* Composio Profiles Modal */}
      <ComposioProfilesModal
        open={isOpen}
        setOpen={setIsOpen}
      />
    </>
  );
}
