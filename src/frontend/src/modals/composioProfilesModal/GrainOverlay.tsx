import React from "react";
import { cn } from "@/utils/utils";

interface GrainOverlayProps {
  className?: string;
}

/**
 * GrainOverlay - Simple overlay component with noise texture
 * Provides premium aesthetic grain effect for glassmorphism cards
 */
export const GrainOverlay: React.FC<GrainOverlayProps> = ({ className }) => {
  return (
    <div
      className={cn("composio-grain-overlay", className)}
      style={{
        backgroundImage: "url('/noise.png')",
      }}
      aria-hidden="true"
    />
  );
};

export default GrainOverlay;
