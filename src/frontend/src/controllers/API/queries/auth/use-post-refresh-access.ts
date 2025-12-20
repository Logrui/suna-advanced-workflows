import { IS_AUTO_LOGIN, LANGFLOW_REFRESH_TOKEN } from "@/constants/constants";
import useAuthStore from "@/stores/authStore";
import type { useMutationFunctionType } from "@/types/api";
import { cookieManager } from "@/utils/cookie-manager";
import { isExternalAuthMode } from "@/utils/iframe-mode";
import { api } from "../../api";
import { getURL } from "../../helpers/constants";
import { UseRequestProcessor } from "../../services/request-processor";

interface IRefreshAccessToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const useRefreshAccessToken: useMutationFunctionType<
  undefined,
  undefined | void,
  IRefreshAccessToken
> = (options?) => {
  const { mutate } = UseRequestProcessor();
  const autoLogin = useAuthStore((state) => state.autoLogin);

  async function refreshAccess(): Promise<IRefreshAccessToken> {
    // Skip refresh in iframe/external auth mode
    // In this mode, the parent app (Suna) manages the auth session
    // and refresh tokens don't work reliably due to cross-origin cookie issues
    let isInExternalAuthMode = false;
    try {
      isInExternalAuthMode = isExternalAuthMode();
    } catch {
      // If we can't detect (e.g., cross-origin), assume we're in iframe mode
      isInExternalAuthMode = true;
    }

    if (isInExternalAuthMode) {
      console.log("[Refresh] Skipping refresh - external auth mode detected (iframe)");
      // Return empty response - the access token should still be valid
      // The parent app will re-embed with a fresh token if needed
      return Promise.reject(new Error("Refresh skipped in external auth mode"));
    }

    // Standard refresh flow for non-iframe usage
    const storedRefreshToken = cookieManager.get(LANGFLOW_REFRESH_TOKEN);

    const res = await api.post<IRefreshAccessToken>(`${getURL("REFRESH")}`, {
      refresh_token: storedRefreshToken,
    });

    // Store the new refresh token
    cookieManager.set(LANGFLOW_REFRESH_TOKEN, res.data.refresh_token);

    return res.data;
  }

  const mutation = mutate(["useRefreshAccessToken"], refreshAccess, {
    ...options,
    retry: IS_AUTO_LOGIN || autoLogin ? 0 : 2,
  });

  return mutation;
};

