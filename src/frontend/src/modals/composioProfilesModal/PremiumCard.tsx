import React from "react";
import { cn } from "@/utils/utils";

interface PremiumCardProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * PremiumCard - Glassmorphism card with OKLCH colors
 * Premium aesthetic wrapper component using composio-profiles.css variables
 */
export const PremiumCard: React.FC<PremiumCardProps> = ({
  children,
  className,
}) => {
  return (
    <div className={cn("composio-premium-card", className)}>
      {children}
    </div>
  );
};

export default PremiumCard;
