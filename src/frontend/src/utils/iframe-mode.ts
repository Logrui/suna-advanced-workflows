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
 * Send a message to the parent window (e.g., Suna) if in iframe mode.
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
    window.history.replaceState({}, "", url.toString());
}
