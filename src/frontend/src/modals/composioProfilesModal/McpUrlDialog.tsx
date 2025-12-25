import { Check, Copy, Eye, EyeOff } from "lucide-react";
import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import BaseModal from "../baseModal";

interface McpUrlDialogProps {
  open: boolean;
  onClose: () => void;
  profileName: string;
  mcpUrl: string;
}

export default function McpUrlDialog({
  open,
  onClose,
  profileName,
  mcpUrl,
}: McpUrlDialogProps): JSX.Element {
  const [isVisible, setIsVisible] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(mcpUrl);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
    }
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      // Reset state when closing
      setIsVisible(false);
      setIsCopied(false);
      onClose();
    }
  };

  return (
    <BaseModal
      open={open}
      setOpen={handleOpenChange}
      size="small"
      className="composio-mcp-url-dialog"
    >
      <BaseModal.Header description="Use this URL to configure the Composio MCP server in your application.">
        <span>Composio MCP URL</span>
      </BaseModal.Header>

      <BaseModal.Content>
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Profile Name
            </label>
            <div className="rounded-md border border-input bg-muted px-3 py-2 text-sm">
              {profileName}
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              MCP Server URL
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 rounded-md border border-input bg-background px-3 py-2 font-mono text-sm">
                {isVisible ? mcpUrl : "••••••••••••••••••••••••••••••••"}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setIsVisible(!isVisible)}
                data-testid="toggle-visibility"
                title={isVisible ? "Hide URL" : "Show URL"}
              >
                {isVisible ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleCopy}
                data-testid="copy-url"
                title="Copy to clipboard"
              >
                {isCopied ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <div className="rounded-md border border-muted bg-muted/50 p-3 text-xs text-muted-foreground">
            <p className="font-medium">Usage Example:</p>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-all">
              {`{
  "mcpServers": {
    "composio": {
      "url": "${isVisible ? mcpUrl : "<your-mcp-url>"}"
    }
  }
}`}
            </pre>
          </div>
        </div>
      </BaseModal.Content>

      <BaseModal.Footer>
        <div className="flex w-full items-center justify-end">
          <Button
            variant="outline"
            onClick={onClose}
            data-testid="mcp-url-dialog-close"
          >
            Close
          </Button>
        </div>
      </BaseModal.Footer>
    </BaseModal>
  );
}
