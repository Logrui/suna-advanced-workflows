
import { customOpenNewTab } from "@/customization/utils/custom-open-new-tab";
import { useState } from "react";
import IconComponent from "../../../../common/genericIconComponent";
import { Button } from "../../../../ui/button";
import type { InputProps } from "../../types";

export default function AuthComponent({
    value,
    disabled = false,
    id = "",
    handleOnNewValue,
}: InputProps<string>): JSX.Element {
    const [loading, setLoading] = useState(false);

    // Determine state based on value
    const isUrl = value && (value.startsWith("http://") || value.startsWith("https://"));
    // Sometimes value is "validated"
    const isConnected = value === "validated";
    // Check for error strings
    const isError = value && typeof value === 'string' && value.startsWith("Error:");

    // Decide label and icon
    const getLabel = () => {
        if (loading) return "Connecting...";
        if (isConnected) return "Connected";
        if (isUrl) return "Authenticate";
        if (isError) return "Retry Connection";
        return "Connect";
    };

    const getIcon = () => {
        if (loading) return "Loader2";
        if (isConnected) return "Check";
        if (isUrl) return "ExternalLink";
        if (isError) return "RefreshCcw";
        return "Link";
    };

    const handleClick = async () => {
        if (isUrl) {
            customOpenNewTab(value);
        } else if (!isConnected) {
            setLoading(true);
            // Trigger a backend update to initiate connection.
            // We pass "connect" to trigger the logic in composio_base.py.
            try {
                await handleOnNewValue({ value: "connect" });
            } catch (error) {
                console.error("Failed to initiate connection:", error);
            } finally {
                setLoading(false);
            }
        }
    };

    return (
        <div className="w-full">
            <Button
                data-testid={`auth-btn-${id}`}
                onClick={handleClick}
                disabled={disabled || isConnected || (loading && !isUrl)}
                variant={isConnected ? "outline" : isError ? "destructive" : "default"}
                className="w-full justify-between"
            >
                <span className="flex items-center gap-2">
                    <IconComponent
                        name={getIcon()}
                        className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
                    />
                    {getLabel()}
                </span>
            </Button>
            {isError && (
                <p className="mt-1 text-xs text-destructive">{value}</p>
            )}
        </div>
    );
}
