import { Outlet } from "react-router-dom";
import AppHeader from "@/components/core/appHeaderComponent";
import useTheme from "@/customization/hooks/use-custom-theme";
import { isExternalAuthMode } from "@/utils/iframe-mode";

export function DashboardWrapperPage() {
  useTheme();
  // Detect if we are in embedded/iframe mode
  const isEmbedded = isExternalAuthMode();
  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      {/* 
        Site header is visually hidden when embedded in Suna (kept in DOM to avoid React issues)
        Using CSS to hide: invisible + h-0 + overflow-hidden makes it visually gone but present in DOM
      */}
      <div className={isEmbedded ? "invisible h-0 overflow-hidden" : ""}>
        <AppHeader />
      </div>

      <div className="flex w-full flex-1 flex-row overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
