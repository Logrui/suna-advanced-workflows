"use client";

import type React from "react";
import { useEffect, useRef, useState } from "react";
import IconComponent from "../../components/common/genericIconComponent";
import SanitizedHTMLWrapper from "../../components/common/sanitizedHTMLWrapper";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/textarea";
import { EDIT_TEXT_PLACEHOLDER } from "../../constants/constants";
import { classNames } from "../../utils/utils";
import BaseModal from "../baseModal";
import { highlightPlaybookVariables } from "../../components/core/parameterRenderComponent/components/playbookComponent/utils/playbookHighlight";

interface PlaybookModalProps {
    field_name: string;
    value: string;
    setValue: (value: string) => void;
    availableVars: string[];
    children: React.ReactNode;
    disabled?: boolean;
    id?: string;
    readonly?: boolean;
}

export default function PlaybookModal({
    field_name = "",
    value,
    setValue,
    availableVars = [],
    children,
    disabled,
    id = "",
    readonly = false,
}: PlaybookModalProps): JSX.Element {
    const [modalOpen, setModalOpen] = useState(false);
    const [inputValue, setInputValue] = useState(value);
    const [isEdit, setIsEdit] = useState(true);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const previewRef = useRef<HTMLDivElement>(null);
    const [scrollPosition, setScrollPosition] = useState(0);

    const { html } = highlightPlaybookVariables(inputValue || "", availableVars);

    useEffect(() => {
        if (typeof value === "string") setInputValue(value);
    }, [value, modalOpen]);

    const handlePreviewClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!isEdit && !readonly) {
            setScrollPosition(e.currentTarget.scrollTop);
            setIsEdit(true);
        }
    };

    useEffect(() => {
        if (isEdit && textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.scrollTop = scrollPosition;
        } else if (!isEdit && previewRef.current) {
            previewRef.current.scrollTop = scrollPosition;
        }
    }, [isEdit, scrollPosition]);

    const handleInsertVariable = (varName: string) => {
        const variableTemplate = `{{${varName}}}`;
        if (textareaRef.current) {
            const start = textareaRef.current.selectionStart;
            const end = textareaRef.current.selectionEnd;
            const newValue =
                inputValue.substring(0, start) +
                variableTemplate +
                inputValue.substring(end);
            setInputValue(newValue);

            // Focus back and move cursor
            setTimeout(() => {
                if (textareaRef.current) {
                    textareaRef.current.focus();
                    const newCursorPos = start + variableTemplate.length;
                    textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
                }
            }, 0);
        } else {
            setInputValue(inputValue + variableTemplate);
        }
    };

    return (
        <BaseModal
            open={modalOpen}
            setOpen={setModalOpen}
            size="x-large"
        >
            <BaseModal.Trigger disable={disabled} asChild>
                {children}
            </BaseModal.Trigger>
            <BaseModal.Header>
                <div className="flex w-full items-start gap-3">
                    <div className="flex items-center">
                        <IconComponent
                            name="BookOpen"
                            className="h-6 w-6 pr-1 text-primary"
                            aria-hidden="true"
                        />
                        <span className="pl-2" data-testid="modal-title">
                            Edit Playbook: {field_name}
                        </span>
                    </div>
                </div>
            </BaseModal.Header>
            <BaseModal.Content overflowHidden>
                <div className={classNames("flex h-full w-full rounded-lg border bg-background")}>
                    {isEdit && !readonly ? (
                        <Textarea
                            id={"modal-" + id}
                            data-testid={"modal-" + id}
                            ref={textareaRef}
                            className="h-full w-full resize-none rounded-lg border-0 bg-transparent p-4 outline-none focus:ring-0"
                            value={inputValue}
                            onBlur={() => {
                                setScrollPosition(textareaRef.current?.scrollTop || 0);
                                // Switch to preview mode on blur
                                setIsEdit(false);
                            }}
                            autoFocus
                            onChange={(event) => {
                                setInputValue(event.target.value);
                            }}
                            placeholder={EDIT_TEXT_PLACEHOLDER}
                        />
                    ) : (
                        <div
                            ref={previewRef}
                            onClick={handlePreviewClick}
                            className="h-full w-full overflow-y-auto p-4 cursor-text"
                        >
                            <SanitizedHTMLWrapper
                                className="m-0 whitespace-pre-wrap text-sm"
                                content={html}
                                suppressWarning={true}
                            />
                        </div>
                    )}
                </div>
            </BaseModal.Content>
            <BaseModal.Footer>
                <div className="flex w-full items-center justify-between">
                    <div className="flex flex-wrap items-center gap-2">
                        <IconComponent name="Braces" className="h-4 w-4 text-primary" />
                        <span className="text-sm font-semibold text-muted-foreground mr-1">Insert:</span>
                        {availableVars.map((v, i) => (
                            <Badge
                                key={i}
                                variant="secondary"
                                className="text-xs cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                                onMouseDown={(e) => e.preventDefault()} // Prevent blur of textarea
                                onClick={() => handleInsertVariable(v)}
                            >
                                {v}
                            </Badge>
                        ))}
                    </div>
                    <Button
                        onClick={() => {
                            setValue(inputValue);
                            setModalOpen(false);
                        }}
                    >
                        Save Playbook
                    </Button>
                </div>
            </BaseModal.Footer>
        </BaseModal>
    );
}
