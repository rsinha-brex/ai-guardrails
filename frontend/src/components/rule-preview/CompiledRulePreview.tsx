"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { paramString, type CompiledRule } from "@/lib/api";
import { cn } from "@/lib/cn";
import { EditableField } from "./EditableField";
import { PrettyParameters } from "./PrettyParameters";

type Props = {
  rule: CompiledRule;
  onSave: (edited: CompiledRule) => void;
  onEdit: () => void;
  saving: boolean;
  /**
   * In the create flow the back-button reads "Edit description" and re-opens
   * the prompt-input step. In the edit-existing-rule flow there's no prompt
   * to go back to — pass `false` to hide it. Defaults to `true` so the
   * existing AddRuleModal call site keeps working.
   */
  showEditPromptButton?: boolean;
};

/**
 * The editable preview card shown after a compile succeeds. Shows the
 * compiled rule's identity (rule_type, name, description, applies-when) and
 * its parameters in human-readable form. Owner can tweak the user-facing
 * text (name, description, applies-when, block_message, instruction)
 * without re-running the compile step.
 */
export function CompiledRulePreview({ rule, onSave, onEdit, saving, showEditPromptButton = true }: Props) {
  const [draft, setDraft] = useState(() => initialDraft(rule));

  useEffect(() => {
    setDraft(initialDraft(rule));
  }, [rule]);

  const dirty =
    draft.name !== rule.name ||
    draft.description !== rule.description ||
    draft.applies_when_description !== rule.applies_when_description ||
    draft.block_message !== paramString(rule.parameters, "block_message") ||
    draft.instruction !== paramString(rule.parameters, "instruction");

  const handleSave = () => {
    const params: Record<string, unknown> = {
      ...(rule.parameters as Record<string, unknown>),
    };
    if ("block_message" in params && draft.block_message !== undefined) {
      params.block_message = draft.block_message;
    }
    if ("instruction" in params && draft.instruction !== undefined) {
      params.instruction = draft.instruction;
    }
    onSave({
      ...rule,
      name: draft.name,
      description: draft.description,
      applies_when_description: draft.applies_when_description,
      parameters: params,
    });
  };

  return (
    <div className="rounded-md border border-accent/40 bg-accent-tint/40 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Check className="size-4 text-accent" />
          <span className="font-mono text-[10px] tracking-widest text-accent uppercase">
            Compiled · {rule.rule_type.replace(/_/g, " ")}
            {rule.confidence === "draft" && " · draft"}
          </span>
        </div>
        {dirty && (
          <span className="font-mono text-[10px] uppercase tracking-wider text-amber">edited</span>
        )}
      </div>

      {rule.confidence === "draft" && (
        <div className="rounded border border-amber/40 bg-amber/10 px-3 py-2 text-xs text-amber-foreground">
          <div className="font-mono text-[10px] uppercase tracking-wider text-amber mb-1">
            Owner action needed
          </div>
          <div className="text-ink">
            We compiled the shape of this rule, but you need to fill in:{" "}
            <span className="font-mono">{(rule.draft_gaps ?? ["specifics"]).join(", ")}</span>. You
            can save it as-is and edit it later, or refine the prompt and try again.
          </div>
        </div>
      )}

      <EditableField
        label="rule name"
        value={draft.name}
        onChange={(v) => setDraft((d) => ({ ...d, name: v }))}
        as="input"
        className="text-ink font-medium text-base"
      />
      <EditableField
        label="description"
        value={draft.description}
        onChange={(v) => setDraft((d) => ({ ...d, description: v }))}
        as="textarea"
        rows={2}
        className="text-sm text-ink-soft"
      />
      <EditableField
        label="applies when"
        value={draft.applies_when_description}
        onChange={(v) => setDraft((d) => ({ ...d, applies_when_description: v }))}
        as="textarea"
        rows={1}
        className="text-xs text-ink-muted"
      />

      <PrettyParameters
        ruleType={rule.rule_type}
        parameters={rule.parameters as Record<string, unknown>}
        blockMessage={draft.block_message}
        onBlockMessageChange={
          draft.block_message !== undefined
            ? (v) => setDraft((d) => ({ ...d, block_message: v }))
            : undefined
        }
        instruction={draft.instruction}
        onInstructionChange={
          draft.instruction !== undefined
            ? (v) => setDraft((d) => ({ ...d, instruction: v }))
            : undefined
        }
      />

      <details className="text-xs">
        <summary className="cursor-pointer text-ink-muted hover:text-ink">Why this rule type?</summary>
        <p className="mt-2 text-ink-soft">{rule.rationale || "(no rationale provided)"}</p>
      </details>
      <details className="text-xs">
        <summary className="cursor-pointer text-ink-muted hover:text-ink">Show raw parameters</summary>
        <pre className="mt-2 rounded-md bg-ink/95 text-bg-elevated text-[11px] font-mono p-3 overflow-auto max-h-[60vh]">
          {JSON.stringify(rule.parameters, null, 2)}
        </pre>
      </details>

      <div className="flex justify-between items-center">
        {showEditPromptButton ? (
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink"
          >
            <ArrowLeft className="size-3" />
            Edit description
          </button>
        ) : (
          <span />
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md bg-ink text-bg-elevated px-3 py-2 text-sm font-medium hover:bg-ink-soft",
            saving && "opacity-60",
          )}
        >
          {saving ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
          {saving ? "Saving…" : "Save rule"}
        </button>
      </div>
    </div>
  );
}

function initialDraft(rule: CompiledRule) {
  return {
    name: rule.name,
    description: rule.description,
    applies_when_description: rule.applies_when_description,
    block_message: paramString(rule.parameters, "block_message"),
    instruction: paramString(rule.parameters, "instruction"),
  };
}
