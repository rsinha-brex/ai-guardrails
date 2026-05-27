"use client";

import { useState } from "react";
import { api, type RuleSummary } from "@/lib/api";
import { cn } from "@/lib/cn";
import { MoreHorizontal, Play, Pencil, Trash2 } from "lucide-react";

type Props = {
  rule: RuleSummary;
  businessId: string;
  onChanged: () => void;
  onTest?: (rule: RuleSummary) => void;
  onEdit?: (rule: RuleSummary) => void;
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

export function RuleCard({ rule, businessId, onChanged, onTest, onEdit }: Props) {
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const toggle = async () => {
    setBusy(true);
    try {
      await api.rules.update(businessId, rule.id, { is_active: !rule.is_active });
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Delete "${rule.name}"?`)) return;
    setBusy(true);
    try {
      await api.rules.remove(businessId, rule.id);
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const testStatus =
    rule.test_case_count === 0
      ? null
      : rule.test_failing > 0
        ? `${rule.test_passing} pass · ${rule.test_failing} fail`
        : `${rule.test_passing} pass`;

  return (
    <div
      onClick={() => onEdit?.(rule)}
      className={cn(
        "rounded-[var(--radius)] border bg-bg-elevated px-5 py-4 shadow-sm transition-colors",
        rule.is_active ? "border-border" : "border-border opacity-70",
        onEdit && "cursor-pointer hover:border-border-strong",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "mt-1 size-2 rounded-full",
            rule.is_active ? "bg-accent" : "bg-ink-faint",
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] tracking-widest text-ink-muted">
              {RULE_TYPE_LABEL[rule.rule_type] || rule.rule_type.toUpperCase()}
            </span>
            {!rule.is_active && (
              <span className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                · Disabled
              </span>
            )}
          </div>
          <h3 className="text-ink font-medium">{rule.name}</h3>
          <p className="text-ink-soft text-sm mt-0.5">{rule.description}</p>
          <div className="text-xs text-ink-muted mt-1.5">
            {testStatus ? testStatus : "No test cases yet"}
            {rule.applies_to_tools.length > 0 && (
              <>
                {" · "}
                <span className="font-mono">{rule.applies_to_tools.join(", ")}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {onTest && (
            <button
              type="button"
              onClick={() => onTest(rule)}
              className="text-xs px-2 py-1 rounded-md text-ink-soft hover:bg-bg-subtle"
            >
              <span className="inline-flex items-center gap-1">
                <Play className="size-3" /> Test
              </span>
            </button>
          )}
          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(rule)}
              className="text-xs px-2 py-1 rounded-md text-ink-soft hover:bg-bg-subtle"
            >
              <span className="inline-flex items-center gap-1">
                <Pencil className="size-3" /> Edit
              </span>
            </button>
          )}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="size-7 grid place-items-center rounded-md text-ink-soft hover:bg-bg-subtle"
              aria-label="More"
            >
              <MoreHorizontal className="size-4" />
            </button>
            {menuOpen && (
              <ul className="absolute right-0 mt-1 w-48 rounded-md border border-border bg-bg-elevated shadow-lg z-30">
                <li
                  className="px-3 py-2 text-sm hover:bg-bg-subtle cursor-pointer"
                  onClick={() => {
                    setMenuOpen(false);
                    toggle();
                  }}
                >
                  {rule.is_active ? "Disable" : "Enable"}
                </li>
                <li
                  className="px-3 py-2 text-sm hover:bg-rose-tint text-rose cursor-pointer flex items-center gap-2"
                  onClick={() => {
                    setMenuOpen(false);
                    remove();
                  }}
                >
                  <Trash2 className="size-3.5" /> Delete
                </li>
              </ul>
            )}
          </div>
        </div>
      </div>
      {busy && <div className="text-[11px] text-ink-faint mt-2">Saving…</div>}
    </div>
  );
}
