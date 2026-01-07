import { regexHighlight } from "@/constants/constants";

export interface ValidationResult {
    valid: boolean;
    usedVariables: string[];
    undefinedVariables: string[];
    unusedVariables: string[];
}

/**
 * Highlights {{variable}} patterns in playbook text.
 * 
 * Logic:
 * 1. Balanced & even-length brace runs >= 2 mean "real variable" for playbook.
 * 2. If length is odd, it's treated as a normal text or escaped brace.
 * 3. Variables NOT in availableVars are marked as invalid.
 */
export function highlightPlaybookVariables(
    text: string,
    availableVars: string[] = []
): { html: string; validation: ValidationResult } {
    const usedVars = new Set<string>();
    const availableVarNames = availableVars.map(v => v.trim());

    const html = (text || "")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(regexHighlight, (match, codeFence, openRun, varName, closeRun) => {
            // 1) Leave ```code``` blocks untouched
            if (codeFence) return match;

            const lenOpen = openRun?.length ?? 0;
            const lenClose = closeRun?.length ?? 0;

            // For Playbook, we target {{var}}, so length must be >= 2 and even for purely "playbook vars"
            // But Langflow's regexHighlight matches any {+ var }+.
            // We'll follow a similar balanced rule: lenOpen === lenClose.
            // If lenOpen >= 2 and even, it's a playbook var.

            const isBalanced = lenOpen === lenClose;
            const isPlaybookVar = isBalanced && lenOpen >= 2 && lenOpen % 2 === 0;

            if (!isPlaybookVar) return match;

            const trimmedVarName = varName.trim();
            usedVars.add(trimmedVarName);

            const isValid = availableVarNames.includes(trimmedVarName);

            // Number of literal braces outside the span (escaped ones)
            // e.g. {{{{var}}}} -> {{ <span>{{var}}</span> }}
            const outerCount = Math.floor((lenOpen - 2) / 2);
            const outerLeft = "{".repeat(outerCount * 2);
            const outerRight = "}".repeat(outerCount * 2);

            const className = isValid
                ? "playbook-variable-valid"
                : "playbook-variable-invalid";

            return (
                `${outerLeft}` +
                `<span class="${className}">{{${varName}}}</span>` +
                `${outerRight}`
            );
        })
        .replace(/\n/g, "<br />");

    const usedVariablesArray = Array.from(usedVars);
    const undefinedVariables = usedVariablesArray.filter(v => !availableVarNames.includes(v));
    const unusedVariables = availableVarNames.filter(v => !usedVars.has(v));

    return {
        html,
        validation: {
            valid: undefinedVariables.length === 0,
            usedVariables: usedVariablesArray,
            undefinedVariables,
            unusedVariables
        }
    };
}
