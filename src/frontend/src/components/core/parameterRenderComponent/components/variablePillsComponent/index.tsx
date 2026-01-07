"use client";

import { useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import ShadTooltip from "@/components/common/shadTooltipComponent";
import { cn } from "@/utils/utils";
import { Copy, Variable } from "lucide-react";
import type { InputProps, VariablePillsComponentType } from "../../types";

interface VariableDefinition {
    name: string;
    type?: string;
    description?: string;
}

export default function VariablePillsComponent({
    id,
    value,
    handleOnNewValue,
    disabled,
    nodeClass,
    variables = [],
    targetField: propsTargetField,
    targetTextareaId: propsTargetTextareaId,
}: InputProps<VariableDefinition[], VariablePillsComponentType>) {
    // Use value as variables if provided, otherwise use variables prop
    const variableList: VariableDefinition[] = Array.isArray(value)
        ? value
        : variables;

    // Extract from nodeClass as fallback (using name/id mapping if possible)
    // Note: We might need the actual field 'name' here for template lookup
    const {
        targetField: templateTargetField,
        targetTextareaId: templateTargetTextareaId
    } = nodeClass?.template?.[id]?.["component_type"] || {};

    const targetField = propsTargetField || templateTargetField;
    const targetTextareaId = propsTargetTextareaId || templateTargetTextareaId;

    const handleInsertVariable = useCallback(
        (varName: string) => {
            const variableTemplate = `{{${varName}}}`;

            // Copy to clipboard
            navigator.clipboard.writeText(variableTemplate);

            // If targetTextareaId is specified, attempt cursor-aware insertion
            if (targetTextareaId) {
                const element = document.getElementById(targetTextareaId) as HTMLTextAreaElement | HTMLInputElement;
                if (element) {
                    const start = element.selectionStart ?? 0;
                    const end = element.selectionEnd ?? 0;
                    const currentValue = element.value;

                    const newValue = currentValue.substring(0, start) + variableTemplate + currentValue.substring(end);

                    // Update value via handleOnNewValue (targeting the field the textarea belongs to)
                    // Note: We assume the textarea belongs to targetField
                    if (targetField) {
                        handleOnNewValue({ value: newValue }, { skipSnapshot: false });

                        // Set focus back and move cursor (need timeout to wait for re-render)
                        setTimeout(() => {
                            element.focus();
                            const newCursorPos = start + variableTemplate.length;
                            element.setSelectionRange(newCursorPos, newCursorPos);
                        }, 0);
                        return;
                    }
                }
            }

            // Fallback: If targetField is specified and we have nodeClass, attempt to insert (append)
            if (targetField && nodeClass?.template?.[targetField]) {
                const currentValue =
                    (nodeClass.template[targetField].value as string) || "";
                // Insert at end with space
                const newValue = currentValue
                    ? `${currentValue} ${variableTemplate}`
                    : variableTemplate;
                handleOnNewValue({ value: newValue }, { skipSnapshot: false });
            }
        },
        [targetField, targetTextareaId, nodeClass, handleOnNewValue, id],
    );

    const getTypeColor = (type?: string): string => {
        switch (type?.toLowerCase()) {
            case "string":
                return "bg-green-500/20 text-green-400 border-green-500/30";
            case "number":
            case "integer":
            case "float":
                return "bg-blue-500/20 text-blue-400 border-blue-500/30";
            case "boolean":
                return "bg-purple-500/20 text-purple-400 border-purple-500/30";
            case "array":
                return "bg-orange-500/20 text-orange-400 border-orange-500/30";
            case "object":
                return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
            default:
                return "bg-muted text-muted-foreground border-border";
        }
    };

    if (!variableList || variableList.length === 0) {
        return (
            <div
                id={id}
                className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 p-3"
            >
                <Variable className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                    No variables available
                </span>
            </div>
        );
    }

    return (
        <div id={id} className="space-y-2">
            <div className="flex flex-wrap gap-2">
                {variableList.map((variable, index) => (
                    <ShadTooltip
                        key={`${variable.name}-${index}`}
                        delayDuration={200}
                        content={
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                                        {`{{${variable.name}}}`}
                                    </code>
                                    {variable.type && (
                                        <Badge variant="secondary" className="text-[10px]">
                                            {variable.type}
                                        </Badge>
                                    )}
                                </div>
                                {variable.description && (
                                    <p className="text-xs text-muted-foreground">
                                        {variable.description}
                                    </p>
                                )}
                                <p className="flex items-center gap-1 text-[10px] text-muted-foreground/70">
                                    <Copy className="h-3 w-3" />
                                    Click to copy & insert
                                </p>
                            </div>
                        }
                    >
                        <Button
                            variant="ghost"
                            size="sm"
                            disabled={disabled}
                            className={cn(
                                "h-7 gap-1.5 border px-2.5 font-mono text-xs",
                                "transition-all duration-200",
                                "hover:scale-105 hover:shadow-sm",
                                getTypeColor(variable.type),
                            )}
                            onClick={() => handleInsertVariable(variable.name)}
                        >
                            <span className="opacity-60">{"{{"}</span>
                            <span>{variable.name}</span>
                            <span className="opacity-60">{"}}"}</span>
                        </Button>
                    </ShadTooltip>
                ))}
            </div>

            {targetField && (
                <p className="text-[10px] text-muted-foreground">
                    Click a variable to insert it into your playbook
                </p>
            )}
        </div>
    );
}
