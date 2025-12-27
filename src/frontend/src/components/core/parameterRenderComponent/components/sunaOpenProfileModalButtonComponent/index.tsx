/**
 * Suna Open Profile Modal Button Component
 *
 * A button that sends a postMessage to the parent Suna window to open the
 * Composio profile management modal. This allows users to manage their
 * Composio profiles directly from the Langflow editor.
 *
 * This is used in EXTERNAL_PROFILES mode as an alternative way to trigger
 * the profile management modal via the iframe-parent communication bridge.
 */

import { useCallback } from "react";
import { ExternalLink, Sparkles } from "lucide-react";
import { isInIframe } from "@/utils/iframe-mode";
import type { InputProps } from "../../types";

// PostMessage types for parent-child communication
const SUNA_MESSAGE_TYPES = {
    OPEN_PROFILE_MODAL: "SUNA_OPEN_PROFILE_MODAL",
} as const;

interface SunaOpenProfileModalButtonProps extends InputProps {
    /**
     * Optional toolkit slug to filter the modal's profile list
     */
    toolkitSlug?: string;
}

export default function SunaOpenProfileModalButtonComponent({
    id,
    disabled,
    helperText,
    toolkitSlug,
}: SunaOpenProfileModalButtonProps) {
    const isIframe = isInIframe();

    const handleOpenInSuna = useCallback(() => {
        if (!window.parent || window.parent === window) {
            console.warn("[SunaOpenProfileModalButton] No parent window found");
            return;
        }

        console.log("[SunaOpenProfileModalButton] Requesting parent to open profile modal", {
            toolkitSlug,
        });

        // Send message to parent Suna window
        window.parent.postMessage(
            {
                type: SUNA_MESSAGE_TYPES.OPEN_PROFILE_MODAL,
                payload: {
                    toolkit: toolkitSlug || null,
                    source: "langflow-open-in-suna-button",
                },
            },
            "*" // In production, specify exact origin
        );
    }, [toolkitSlug]);

    // Don't render if not in iframe mode
    if (!isIframe) {
        return (
            <div className="flex items-center gap-2 rounded-lg bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                <span>Not running in embedded mode</span>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-2">
            {/* Main action button */}
            <button
                id={id}
                onClick={handleOpenInSuna}
                disabled={disabled}
                className={`
                    group relative flex w-full items-center justify-center gap-2 
                    overflow-hidden rounded-xl border border-primary/30 
                    bg-gradient-to-r from-primary/5 to-primary/10 
                    px-4 py-2.5 text-sm font-medium text-primary 
                    transition-all duration-300
                    hover:border-primary/50 hover:from-primary/10 hover:to-primary/15 hover:shadow-md
                    disabled:cursor-not-allowed disabled:opacity-50
                `}
            >
                {/* Subtle shine effect */}
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-500 group-hover:translate-x-full" />

                <Sparkles className="h-4 w-4" />
                <span>Open in Suna</span>
                <ExternalLink className="h-3.5 w-3.5 opacity-60" />
            </button>

            {/* Helper text */}
            {helperText && (
                <p className="text-xs text-muted-foreground">{helperText}</p>
            )}
        </div>
    );
}
