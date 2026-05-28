"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api, type ConversationSummary } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useBusinessId } from "@/lib/use-business-id";
import { useResource } from "@/lib/use-resource";
import { STATUS_DOT_CLASS, STATUS_LABEL, STATUS_PILL_CLASS, statusKeyOr } from "@/lib/status-styles";
import { ChevronRight, X } from "lucide-react";

const OUTCOME_LABEL = STATUS_LABEL;
const OUTCOME_DOT = STATUS_DOT_CLASS;
const OUTCOME_BADGE = STATUS_PILL_CLASS;

export default function ActivityPage() {
  const { businessId } = useBusinessId();
  const [outcome, setOutcome] = useState<string | null>("blocked");

  const { data: conversations, error, refetch } = useResource<ConversationSummary[]>(
    () => (businessId ? api.activity.list(businessId, outcome ? { outcome } : {}) : Promise.resolve([])),
    [businessId, outcome],
  );

  // 3-second polling on top of the initial load, paused when the tab is hidden.
  useEffect(() => {
    if (!businessId) return;
    const id = window.setInterval(() => {
      if (!document.hidden) refetch();
    }, 3000);
    return () => window.clearInterval(id);
  }, [businessId, outcome, refetch]);

  return (
    <AppShell>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">Activity</h1>
          <p className="text-ink-muted mt-1 text-sm">
            {conversations
              ? `${conversations.length} conversations${outcome ? ` · filter: ${OUTCOME_LABEL[statusKeyOr(outcome)]}` : ""}`
              : "Loading…"}
          </p>
        </div>
      </div>

      {/* Filter chip row */}
      <div className="flex items-center gap-2 mb-4">
        <FilterChip
          active={outcome === "blocked"}
          label="Outcome"
          value="Blocked"
          onSelect={() => setOutcome(outcome === "blocked" ? null : "blocked")}
        />
        <FilterChip
          active={outcome === "accepted"}
          label="Outcome"
          value="Allowed"
          onSelect={() => setOutcome(outcome === "accepted" ? null : "accepted")}
        />
        <FilterChip
          active={outcome === "open"}
          label="Outcome"
          value="Open"
          onSelect={() => setOutcome(outcome === "open" ? null : "open")}
        />
        {outcome && (
          <button
            type="button"
            onClick={() => setOutcome(null)}
            className="text-xs text-ink-muted underline"
          >
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-rose/40 bg-rose-tint p-3 text-rose text-sm mb-4">
          {error}
        </div>
      )}

      {conversations && conversations.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-ink-muted">No conversations match these filters yet.</p>
        </div>
      )}

      <div className="rounded-[var(--radius)] border border-border bg-bg-elevated overflow-hidden">
        {conversations?.map((c) => (
          <Link
            key={c.id}
            href={`/activity/${c.id}?business=${c.business_id}`}
            className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-b-0 hover:bg-bg-subtle transition-colors"
          >
            <span className={cn("size-2 rounded-full", OUTCOME_DOT[statusKeyOr(c.outcome)])} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-ink font-medium">{c.customer_identifier}</span>
                <span className="text-xs text-ink-muted">
                  {new Date(c.last_message_at).toLocaleString()}
                </span>
                {c.is_test && (
                  <span className="text-[10px] font-mono uppercase tracking-widest text-ink-faint">
                    test
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                <span
                  className={cn(
                    "text-[10px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded",
                    OUTCOME_BADGE[statusKeyOr(c.outcome)],
                  )}
                >
                  {OUTCOME_LABEL[statusKeyOr(c.outcome)]}
                </span>
                <span className="text-xs text-ink-muted">{c.message_count} messages</span>
              </div>
            </div>
            <ChevronRight className="size-4 text-ink-faint" />
          </Link>
        ))}
      </div>
    </AppShell>
  );
}

function FilterChip({
  active,
  label,
  value,
  onSelect,
}: {
  active: boolean;
  label: string;
  value: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs",
        active
          ? "border-ink bg-ink text-bg-elevated"
          : "border-border bg-bg-elevated text-ink-soft hover:border-border-strong",
      )}
    >
      <span className="opacity-70">{label}:</span>
      <span className="font-medium">{value}</span>
      {active && <X className="size-3" />}
    </button>
  );
}
