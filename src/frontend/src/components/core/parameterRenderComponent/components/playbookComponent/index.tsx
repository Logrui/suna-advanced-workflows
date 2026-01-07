"use client";

import ForwardedIconComponent from "@/components/common/genericIconComponent";
import SanitizedHTMLWrapper from "@/components/common/sanitizedHTMLWrapper";
import PlaybookModal from "@/modals/playbookModal";
import { cn } from "../../../../../utils/utils";
import { Button } from "../../../../ui/button";
import { getPlaceholder } from "../../helpers/get-placeholder-disabled";
import type { InputProps, TextAreaComponentType } from "../../types";
import { highlightPlaybookVariables } from "./utils/playbookHighlight";

const playbookContentClasses = {
    base: "overflow-hidden text-clip whitespace-nowrap bg-background h-fit max-h-28 rounded-md border border-input p-2 cursor-pointer",
    editNode: "input-edit-node py-2",
    normal: "primary-input text-primary",
    disabled: "disabled-state",
};

export default function PlaybookAreaComponent({
    value,
    disabled,
    handleOnNewValue,
    id = "",
    placeholder,
    nodeClass,
    name,
}: InputProps<string, TextAreaComponentType>): JSX.Element {

    // Extract available variables from the node's template if available
    const availableVarsPill = Object.values(nodeClass?.template || {}).find(
        (input: any) => input.type === "variable_pills" || input.name === "available_variables"
    ) as any;
    const availableVars = (availableVarsPill?.value || []).map((v: any) => v.name);

    const { html } = highlightPlaybookVariables(value || "", availableVars);

    const renderPlaybookText = () => (
        <span
            id={id}
            data-testid={id}
            className={cn(
                playbookContentClasses.base,
                playbookContentClasses.normal,
                disabled && playbookContentClasses.disabled,
            )}
        >
            {value !== "" ? (
                <SanitizedHTMLWrapper
                    className="m-0 whitespace-pre-wrap p-0 text-xs text-left"
                    content={html}
                    suppressWarning={true}
                />
            ) : (
                <span className="text-sm text-muted-foreground block text-left">
                    {getPlaceholder(disabled, placeholder || "Type your playbook here...")}
                </span>
            )}
        </span>
    );

    return (
        <div className={cn("w-full transition-all hover:ring-1 hover:ring-primary/20 rounded-md", disabled && "pointer-events-none")}>
            <PlaybookModal
                id={id}
                field_name={name || "playbook"}
                value={value || ""}
                setValue={(newValue) => handleOnNewValue({ value: newValue })}
                availableVars={availableVars}
                disabled={disabled}
            >
                <Button
                    unstyled
                    className="w-full"
                    data-testid="button_open_playbook_modal"
                >
                    <div className="relative w-full group">
                        {renderPlaybookText()}
                        <ForwardedIconComponent
                            name="Maximize2"
                            className="absolute right-2 bottom-2 h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        />
                    </div>
                </Button>
            </PlaybookModal>
        </div>
    );
}
