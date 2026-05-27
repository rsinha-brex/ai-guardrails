"use client";

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";
import { api, type RuleSummary } from "@/lib/api";
import { cn } from "@/lib/cn";
import { EditableField } from "./rule-preview/EditableField";
import { StructuredParametersEditor } from "./rule-preview/StructuredParametersEditor";

type Props = {
  rule: RuleSummary;
  businessId: string;
  onClose: () => void;
  onSaved: () => void;
};

const RULE_TYPE_LABEL: Record<string, string> = {
  business_hours: "BUSINESS HOURS",
  service_area_zip: "SERVICE AREA",
  services_offered: "SERVICES",
  customer_eligibility: "ELIGIBILITY",
  lead_time_minimum: "LEAD TIME",
  conditional_block: "CONDITIONAL · LIVE",
  output_constraint: "OUTPUT GUIDANCE",
};

/**
 * Edit-existing-rule modal. Reuses the rule-preview EditableField for
 * name / description / applies-when, and the new StructuredParametersEditor
 * for typed-rule parameters (hours, ZIPs, services, lead times, etc.).
 * On save, PATCHes the rule with the editable subset.
 */
export function EditRuleModal({ rule, businessId, onClose, onSaved }: Props) {
  const [name, setName] = useState(rule.name);
  const [description, setDescription] = useState(rule.description);
  const [appliesWhen, setAppliesWhen] = useState(rule.applies_when_description);
  const [parameters, setParameters] = useState<Record<string, unknown>>(
    rule.parameters as Record<string, unknown>,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    name !== rule.name ||
    description !== rule.description ||
    appliesWhen !== rule.applies_when_description ||
    JSON.stringify(parameters) !== JSON.stringify(rule.parameters);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.rules.update(businessId, rule.id, {
        name,
        description,
        applies_when_description: appliesWhen,
        parameters,
      });
      onSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-ink/30 backdrop-blur-[1px] p-6 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[88vh] rounded-[var(--radius-lg)] bg-bg-elevated shadow-lg overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-xl text-ink">Edit rule</h3>
              {dirty && (
                <span className="font-mono text-[10px] uppercase tracking-wider text-amber">
                  edited
                </span>
              )}
            </div>
            <p className="text-xs text-ink-muted mt-0.5">
              {RULE_TYPE_LABEL[rule.rule_type] || rule.rule_type} · changes save to this business only
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="size-8 grid place-items-center rounded-md hover:bg-bg-subtle text-ink-muted"
          >
            <X className="size-4" />
          </button>
        </div>

        <section className="p-5 space-y-4 overflow-y-auto">
          {error && (
            <div className="rounded-md border border-rose/40 bg-rose-tint p-3 text-rose text-sm">
              {error}
            </div>
          )}

          <div className="space-y-3 rounded-md border border-border bg-bg-elevated p-4">
            <EditableField
              label="rule name"
              value={name}
              onChange={setName}
              as="input"
              className="text-ink font-medium text-base"
            />
            <EditableField
              label="description"
              value={description}
              onChange={setDescription}
              as="textarea"
              rows={2}
              className="text-sm text-ink-soft"
            />
            <EditableField
              label="applies when"
              value={appliesWhen}
              onChange={setAppliesWhen}
              as="textarea"
              rows={1}
              className="text-xs text-ink-muted"
            />
          </div>

          <StructuredParametersEditor
            ruleType={rule.rule_type}
            parameters={parameters}
            onChange={setParameters}
          />

          <details className="text-xs">
            <summary className="cursor-pointer text-ink-muted hover:text-ink">
              Show raw parameters (read-only)
            </summary>
            <pre className="mt-2 rounded-md bg-ink/95 text-bg-elevated text-[11px] font-mono p-3 overflow-auto max-h-[40vh]">
              {JSON.stringify(parameters, null, 2)}
            </pre>
          </details>
        </section>

        <div className="px-5 py-3 border-t border-border flex justify-end shrink-0">
          <button
            type="button"
            onClick={save}
            disabled={saving || !dirty}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md bg-ink text-bg-elevated px-3 py-2 text-sm font-medium hover:bg-ink-soft",
              (saving || !dirty) && "opacity-60",
            )}
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
