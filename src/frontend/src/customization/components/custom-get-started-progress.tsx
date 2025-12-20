import type { Users } from "@/types/api";

export function CustomGetStartedProgress({
  userData,
  isGithubStarred,
  isDiscordJoined,
  handleDismissDialog,
}: {
  userData: Users;
  isGithubStarred: boolean;
  isDiscordJoined: boolean;
  handleDismissDialog: () => void;
}) {
  // Disabled for Kortix Advanced Workflows - no external links
  return <></>;
}

export default CustomGetStartedProgress;
