import { useEffect, useRef, useState } from "react";
import useAlertStore from "@/stores/alertStore";
import { useCreateProfile, useMarkProfileConnected } from "@/controllers/API/composio";
import BaseModal from "../baseModal";
import { Button } from "@/components/ui/button";
import IconComponent from "@/components/common/genericIconComponent";

type Step = "toolkit" | "name" | "oauth" | "success" | "error";

interface ComposioConnectorProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * OAuth wizard component for connecting Composio profiles
 * 4-step flow: Toolkit Selection → Profile Name → OAuth Popup → Success
 */
export function ComposioConnector({
  open,
  onClose,
  onSuccess,
}: ComposioConnectorProps): JSX.Element {
  // =========================================================================
  // State Management
  // =========================================================================
  const [currentStep, setCurrentStep] = useState<Step>("toolkit");
  const [selectedToolkit, setSelectedToolkit] = useState<string>("");
  const [profileName, setProfileName] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [createdProfileId, setCreatedProfileId] = useState<string>("");

  // Refs for popup handling
  const popupRef = useRef<Window | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // API mutations
  const createProfileMutation = useCreateProfile();
  const markConnectedMutation = useMarkProfileConnected();

  // Stores
  const setSuccessData = useAlertStore((state) => state.setSuccessData);
  const setErrorData = useAlertStore((state) => state.setErrorData);

  // =========================================================================
  // Effects
  // =========================================================================

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Reset form when modal closes
  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open]);

  // =========================================================================
  // Handlers
  // =========================================================================

  const resetForm = () => {
    setCurrentStep("toolkit");
    setSelectedToolkit("");
    setProfileName("");
    setError("");
    setIsLoading(false);
    setCreatedProfileId("");
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  /**
   * Step 1: Validate toolkit selection → proceed to name step
   */
  const handleToolkitSelect = (toolkit: string) => {
    if (!toolkit.trim()) {
      setError("Please select a toolkit");
      return;
    }
    setSelectedToolkit(toolkit);
    setError("");
    setCurrentStep("name");
  };

  /**
   * Step 2: Validate profile name → create profile on backend
   */
  const handleProfileNameSubmit = async () => {
    if (!profileName.trim()) {
      setError("Please enter a profile name");
      return;
    }

    if (!selectedToolkit) {
      setError("Toolkit not selected");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      // Call backend to create profile
      const response = await createProfileMutation.mutateAsync({
        toolkit_slug: selectedToolkit,
        profile_name: profileName,
        mcp_url: "", // Backend will generate this
        connected_account_id: "", // Will be set during OAuth
        composio_user_id: "", // Will be set during OAuth
        is_connected: false,
      });

      if (!response.success) {
        throw new Error(response.message || "Failed to create profile");
      }

      setCreatedProfileId(response.profile_id);

      // Check if we have an OAuth redirect URL
      if (response.redirect_url) {
        setCurrentStep("oauth");
        // Automatically open OAuth popup
        setTimeout(() => handleOpenOAuthPopup(response.redirect_url!), 500);
      } else {
        // No OAuth redirect URL - mark as success
        setCurrentStep("success");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      setError(errorMsg);
      setCurrentStep("error");
      setErrorData({
        title: "Failed to create profile",
        list: [errorMsg],
      });
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Step 3: Open OAuth popup window
   */
  const handleOpenOAuthPopup = (redirectUrl: string) => {
    try {
      // Open popup window
      popupRef.current = window.open(
        redirectUrl,
        "composio-oauth",
        "width=600,height=700,scrollbars=yes,resizable=yes"
      );

      if (!popupRef.current) {
        setError(
          "Popup blocked. Please allow popups and try again."
        );
        setCurrentStep("error");
        return;
      }

      // Poll for popup closure
      pollIntervalRef.current = setInterval(async () => {
        if (popupRef.current && popupRef.current.closed) {
          clearInterval(pollIntervalRef.current!);
          pollIntervalRef.current = null;

          // Popup closed, now mark profile as connected
          try {
            await markConnectedMutation.mutateAsync(createdProfileId);
            setCurrentStep("success");

            // Show success notification
            setSuccessData({
              title: `Profile "${profileName}" connected successfully!`,
            });

            // Call onSuccess callback
            if (onSuccess) {
              onSuccess();
            }
          } catch (err) {
            const errorMsg =
              err instanceof Error ? err.message : "Verification failed";
            setError(errorMsg);
            setCurrentStep("error");
            setErrorData({
              title: "Connection verification failed",
              list: [errorMsg],
            });
          }
        }
      }, 1000); // Poll every second
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Popup error";
      setError(errorMsg);
      setCurrentStep("error");
    }
  };

  const handleRetry = () => {
    setError("");
    setCurrentStep("name");
  };

  // =========================================================================
  // Render Steps
  // =========================================================================

  const renderToolkitStep = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">
          Select a Toolkit
        </label>
        <input
          type="text"
          placeholder="e.g., gmail, slack, github..."
          value={selectedToolkit}
          onChange={(e) => setSelectedToolkit(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="outline" onClick={handleClose}>
          Cancel
        </Button>
        <Button onClick={() => handleToolkitSelect(selectedToolkit)}>
          Next
        </Button>
      </div>
    </div>
  );

  const renderNameStep = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">
          Profile Name
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Give this connection a memorable name (e.g., "Work Gmail", "Personal
          Slack")
        </p>
        <input
          type="text"
          placeholder="Enter profile name..."
          value={profileName}
          onChange={(e) => setProfileName(e.target.value)}
          disabled={isLoading}
          autoFocus
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>

      <div className="flex gap-2 justify-end">
        <Button
          variant="outline"
          onClick={() => setCurrentStep("toolkit")}
          disabled={isLoading}
        >
          Back
        </Button>
        <Button onClick={handleProfileNameSubmit} disabled={isLoading}>
          {isLoading ? (
            <>
              <IconComponent
                name="Loader2"
                className="h-4 w-4 animate-spin mr-2"
              />
              Creating...
            </>
          ) : (
            "Connect"
          )}
        </Button>
      </div>
    </div>
  );

  const renderOAuthStep = () => (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <div className="flex gap-2">
          <IconComponent
            name="Info"
            className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5"
          />
          <div>
            <p className="font-medium text-blue-900">OAuth in Progress</p>
            <p className="text-sm text-blue-700 mt-1">
              A popup window should have opened. Please complete the
              authentication in the popup. This window will automatically
              update once you're done.
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <Button
          variant="outline"
          onClick={() => {
            if (popupRef.current && !popupRef.current.closed) {
              popupRef.current.focus();
            }
          }}
        >
          <IconComponent name="ExternalLink" className="h-4 w-4 mr-2" />
          Focus Popup
        </Button>
      </div>
    </div>
  );

  const renderSuccessStep = () => (
    <div className="space-y-4">
      <div className="bg-green-50 border border-green-200 rounded-md p-4">
        <div className="flex gap-2">
          <IconComponent
            name="Check"
            className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5"
          />
          <div>
            <p className="font-medium text-green-900">Connection Successful!</p>
            <p className="text-sm text-green-700 mt-1">
              Your profile "{profileName}" has been connected to {selectedToolkit}.
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <Button onClick={handleClose}>
          Done
        </Button>
      </div>
    </div>
  );

  const renderErrorStep = () => (
    <div className="space-y-4">
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex gap-2">
          <IconComponent
            name="AlertCircle"
            className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5"
          />
          <div>
            <p className="font-medium text-red-900">Connection Failed</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="outline" onClick={handleClose}>
          Cancel
        </Button>
        <Button onClick={handleRetry} variant="destructive">
          Try Again
        </Button>
      </div>
    </div>
  );

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <BaseModal open={open} setOpen={handleClose} size="medium">
      <BaseModal.Header description={`Step ${currentStep === "toolkit" ? 1 : currentStep === "name" ? 2 : currentStep === "oauth" ? 3 : 4} of 4`}>
        <span className="font-semibold">Connect Composio Profile</span>
      </BaseModal.Header>

      <BaseModal.Content>
        {currentStep === "toolkit" && renderToolkitStep()}
        {currentStep === "name" && renderNameStep()}
        {currentStep === "oauth" && renderOAuthStep()}
        {currentStep === "success" && renderSuccessStep()}
        {currentStep === "error" && renderErrorStep()}
      </BaseModal.Content>
    </BaseModal>
  );
}

export default ComposioConnector;
