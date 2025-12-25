//suna-advanced-workflows:start

/**
 * Utilities for detecting and handling iframe embedding mode.
 * Used when Advanced Workflows is embedded inside a parent application (like Suna).
 */

/**
 * Check if the current window is running inside an iframe.
 */
export function isInIframe(): boolean {
    try {
        return window.self !== window.top;
    } catch {
        // Cross-origin iframe will throw a security error
        return true;
    }
}

/**
 * Check if the app was loaded with an external authentication token.
 * This indicates the app is being used in embedded/integration mode.
 */
export function isExternalAuthMode(): boolean {
    const params = new URLSearchParams(window.location.search);
    return params.has("token") || isInIframe();
}

/**
 * Get the external token from URL parameters if present.
 */
export function getExternalToken(): string | null {
    const params = new URLSearchParams(window.location.search);
    return params.get("token");
}

/**
 * Get the external refresh token from URL parameters if present.
 */
export function getExternalRefreshToken(): string | null {
    const params = new URLSearchParams(window.location.search);
    return params.get("refresh_token");
}

/**
 * Send a message to the parent window (e.g., Suna Kortix or other embedded parent application) if in iframe mode.
 * @param type - The type of message (e.g., 'advanced-workflows:ready', 'advanced-workflows:error')
 * @param data - Optional additional data to include in the message
 */
export function notifyParent(
    type: string,
    data?: Record<string, unknown>,
): void {
    if (isInIframe() && window.parent) {
        window.parent.postMessage({ type, ...data }, "*");
    }
}

/**
 * Remove token parameters from the URL without reloading the page.
 * This is called after the token has been consumed to clean up the URL.
 */
export function cleanTokenFromUrl(): void {
    const url = new URL(window.location.href);
    url.searchParams.delete("token");
    url.searchParams.delete("refresh_token");
    url.searchParams.delete("suna_token");
    window.history.replaceState({}, "", url.toString());
}

// ═══════════════════════════════════════════════════════════════════════════
// Suna Kortix Token Functions
// These functions manage the Suna JWT token passed via URL parameter.
// This allows Langflow to call Suna's API directly (e.g., for Composio profiles).
// ═══════════════════════════════════════════════════════════════════════════

import { cookieManager } from "./cookie-manager";
import { SUNA_ACCESS_TOKEN } from "@/constants/constants";

/**
 * Get the Suna token from URL parameters if present.
 * This token is passed by the Suna parent window and is valid for Suna API calls.
 */
export function getSunaToken(): string | null {
    const params = new URLSearchParams(window.location.search);
    return params.get("suna_token");
}

/**
 * Store the Suna token in cookies for later use.
 * Called during auth initialization when the token is present in URL.
 */
export function storeSunaToken(): void {
    const token = getSunaToken();
    if (token) {
        cookieManager.set(SUNA_ACCESS_TOKEN, token);
        console.log("[iframe-mode] Suna token stored for API calls");
    }
}

/**
 * Get the stored Suna token from cookies.
 * Used by the Suna API client to make authenticated requests.
 */
export function getStoredSunaToken(): string | null {
    return cookieManager.get(SUNA_ACCESS_TOKEN) || null;
}

/**
 * Check if Suna integration is available.
 * Returns true if we're in iframe mode and have a Suna token.
 */
export function isSunaIntegrationAvailable(): boolean {
    return isInIframe() && !!getStoredSunaToken();
}

//suna-advanced-workflows:end
