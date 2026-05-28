"use client";

import { useState } from "react";
import { X, Sparkles, Loader2 } from "lucide-react";
import { api, type CompiledRule, type CompileFailure } from "@/lib/api";
import { CompiledRulePreview } from "./rule-preview";

type Props = {
  businessId: string;
  onClose: () => void;
  onCreated: () => void;
};

// Each template seeds the prompt textbox with sample wording and lets the
// compile agent pick the right rule_type. The `id` is a UI key, not a rule
// type — entries like "seasonal" or "emergency_bypass" route to
// conditional_block via the LLM compiler.
const TEMPLATES = [
  {
    id: "business_hours",
    title: "Business hours",
    hint: "When you're open",
  },
  {
    id: "service_area_zip",
    title: "Service area",
    hint: "ZIP codes you cover",
  },
  {
    id: "services_offered",
    title: "Services offered",
    hint: "What you actually do",
  },
  {
    id: "customer_eligibility",
    title: "Customer eligibility",
    hint: "Homeowner / member / etc.",
  },
  {
    id: "lead_time_minimum",
    title: "Lead time",
    hint: "Minimum advance notice",
  },
  {
    id: "conditional_block",
    title: "Custom condition",
    hint: "If/when triggers — e.g. \"Sundays unless emergency\"",
  },
  {
    id: "output_constraint",
    title: "Communication style",
    hint: "How the agent talks",
  },
  {
    id: "seasonal",
    title: "Seasonal closure",
    hint: "Months when you don't operate",
  },
  {
    id: "membership_only",
    title: "Members-only feature",
    hint: "Reserve service for members",
  },
  {
    id: "emergency_bypass",
    title: "Emergency bypass",
    hint: "Skip rules during emergencies",
  },
];

const SAMPLE_PROMPTS: Record<string, string> = {
  business_hours: "We're open Mon–Fri 8 AM to 6 PM, Saturdays 9–4. Closed Sunday.",
  service_area_zip: "Only book inside ZIP codes 32801, 32802, 32803.",
  services_offered: "We do HVAC, plumbing, and electrical.",
  customer_eligibility: "Customer must be the homeowner.",
  lead_time_minimum: "HVAC installs need at least 48 hours of advance notice.",
  output_constraint: "Always mention free in-home consultations.",
  conditional_block: "After 6 PM, only book emergency calls.",
  seasonal: "We close pool services from November through March.",
  membership_only: "Only Care Club members get after-hours emergency service.",
  emergency_bypass: "Standard appointments need 48 hours notice but emergencies are exempt.",
};

export function AddRuleModal({ businessId, onClose, onCreated }: Props) {
  const [prompt, setPrompt] = useState("");
  const [compiling, setCompiling] = useState(false);
  const [compiled, setCompiled] = useState<CompiledRule | null>(null);
  const [failure, setFailure] = useState<CompileFailure | null>(null);
  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const pickTemplate = (t: (typeof TEMPLATES)[number]) => {
    setPrompt(SAMPLE_PROMPTS[t.id] || "");
    setCompiled(null);
    setFailure(null);
  };

  const generate = async () => {
    if (!prompt.trim()) return;
    setCompiling(true);
    setServerError(null);
    setFailure(null);
    setCompiled(null);
    try {
      const res = await api.rules.compile(businessId, prompt.trim());
      if (res.kind === "compiled") setCompiled(res.rule);
      else setFailure(res.failure);
    } catch (e) {
      setServerError(String(e));
    } finally {
      setCompiling(false);
    }
  };

  const save = async (edited: CompiledRule) => {
    setSaving(true);
    setServerError(null);
    try {
      const res = await api.rules.create(businessId, { compiled: edited });
      if (res.failure) setFailure(res.failure);
      else onCreated();
    } catch (e) {
      setServerError(String(e));
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
        className="w-full max-w-4xl max-h-[88vh] rounded-[var(--radius-lg)] bg-bg-elevated shadow-lg overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <h3 className="font-display text-xl text-ink">Add a new rule</h3>
          <button
            type="button"
            onClick={onClose}
            className="size-8 grid place-items-center rounded-md hover:bg-bg-subtle text-ink-muted"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] flex-1 overflow-hidden">
          <aside className="bg-accent-tint/60 border-r border-border p-4 overflow-y-auto max-h-full">
            <div className="font-mono text-[10px] tracking-widest text-ink-muted mb-3">
              START FROM A TEMPLATE
            </div>
            <ul className="space-y-1">
              {TEMPLATES.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => pickTemplate(t)}
                    className="w-full text-left px-3 py-2 rounded-md hover:bg-bg-elevated text-sm border border-transparent hover:border-border"
                  >
                    <div className="text-ink font-medium">{t.title}</div>
                    <div className="text-xs text-ink-muted">{t.hint}</div>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <section className="p-5 space-y-4 overflow-y-auto">
            <div>
              <h4 className="font-display text-lg text-ink mb-1">Describe the rule</h4>
              <p className="text-xs text-ink-muted">
                Plain English works. The compiler will turn it into the right rule type.
              </p>
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Don't propose same-day HVAC installations. We need at least 48 hours."
              rows={4}
              className="w-full rounded-md border border-border bg-bg p-3 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={generate}
                disabled={compiling || !prompt.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-accent text-bg-elevated px-3 py-2 text-sm font-medium hover:bg-accent-soft disabled:opacity-50"
              >
                {compiling ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Sparkles className="size-4" />
                )}
                {compiling ? "Compiling…" : "Generate rule"}
              </button>
            </div>

            {failure && (
              <div className="rounded-md border border-amber/40 bg-amber-tint p-3 text-amber text-sm">
                <div className="font-medium mb-1">A few clarifying questions</div>
                <ul className="list-disc pl-5 text-amber/90 space-y-0.5">
                  {failure.suggested_clarifications.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
                {failure.rationale && (
                  <div className="text-xs text-amber/80 mt-2 italic">{failure.rationale}</div>
                )}
              </div>
            )}

            {compiled && (
              <CompiledRulePreview
                rule={compiled}
                onSave={save}
                onEdit={() => setCompiled(null)}
                saving={saving}
              />
            )}

            {serverError && (
              <div className="rounded-md border border-rose/40 bg-rose-tint p-3 text-rose text-sm">
                {serverError}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

