"use client";

import { cn } from "@/lib/cn";
import type { AuditEvent } from "@/lib/api";
import { STATUS_LABEL_UPPER, STATUS_PILL_CLASS, statusKeyOr } from "@/lib/status-styles";
import {
  Loader2,
  Ban,
  CheckCircle2,
  ArrowRight,
  Info,
  HelpCircle,
  AlertCircle,
} from "lucide-react";

const ICON_FOR_OUTCOME: Record<string, React.ReactNode> = {
  accepted: <CheckCircle2 className="size-3.5" />,
  blocked: <Ban className="size-3.5" />,
  needs_info: <HelpCircle className="size-3.5" />,
  info: <Info className="size-3.5" />,
  failed: <AlertCircle className="size-3.5" />,
};

export function LiveActivityRail({
  events,
  streaming,
}: {
  events: AuditEvent[];
  streaming: boolean;
}) {
  return (
    <aside className="rounded-[var(--radius-lg)] border border-border bg-bg-elevated overflow-hidden flex flex-col">
      <header className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-ink">Live activity</div>
          <div className="text-xs text-ink-muted">
            {events.length} event{events.length === 1 ? "" : "s"} · tool calls + rule fires
          </div>
        </div>
        {streaming && (
          <div className="text-[10px] font-mono uppercase tracking-widest text-accent flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-accent animate-pulse" /> live
          </div>
        )}
      </header>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {events.length === 0 && !streaming && (
          <div className="text-ink-muted text-xs italic px-2 py-6 text-center">
            No tool activity yet. Send a message to see the agent's tool calls and rule fires here.
          </div>
        )}
        {streaming && events.length === 0 && (
          <div className="flex items-center gap-2 px-2 py-3 text-ink-muted text-xs">
            <Loader2 className="size-3 animate-spin" /> agent thinking…
          </div>
        )}
        {events.map((e) => (
          <ActivityCard key={e.id} event={e} />
        ))}
      </div>
    </aside>
  );
}

function ActivityCard({ event }: { event: AuditEvent }) {
  const summary = humanSummary(event);
  const detailRows = detailLines(event);
  const time = new Date(event.fired_at).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      className={cn(
        "rounded-md border px-2.5 py-2 text-xs space-y-1",
        STATUS_PILL_CLASS[statusKeyOr(event.outcome)],
      )}
    >
      <div className="flex items-center gap-1.5">
        {ICON_FOR_OUTCOME[event.outcome] || ICON_FOR_OUTCOME.info}
        <span className="font-mono text-[11px] font-medium">
          {event.tool_name || event.event_type}
        </span>
        <span className="ml-auto text-[10px] opacity-70 font-mono">{time}</span>
      </div>
      {summary && <div className="text-[12px] leading-snug">{summary}</div>}
      {event.fired_rule_name && (
        <div className="text-[11px] opacity-90">
          <span className="font-mono uppercase tracking-wider opacity-70 mr-1">rule</span>
          {event.fired_rule_name}
        </div>
      )}
      {event.outcome !== "info" && event.outcome !== "accepted" && (
        <div className="text-[10px] uppercase tracking-widest font-mono opacity-80">
          {STATUS_LABEL_UPPER[statusKeyOr(event.outcome)]}
        </div>
      )}
      {event.internal_reason && (
        <div className="text-[11px] italic opacity-80">{event.internal_reason}</div>
      )}
      {event.required_fields && event.required_fields.length > 0 && (
        <div className="text-[11px] opacity-90">
          <span className="font-mono uppercase tracking-wider opacity-70 mr-1">needs</span>
          {event.required_fields.join(", ")}
        </div>
      )}
      {detailRows.length > 0 && (
        <details className="text-[11px]">
          <summary className="cursor-pointer opacity-70 select-none">args</summary>
          <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 font-mono text-[10px]">
            {detailRows.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="opacity-70">{k}</dt>
                <dd className="break-all">{v}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  );
}

function humanSummary(e: AuditEvent): string | null {
  // Surface the most useful one-liner per event type.
  if (e.tool_name === "update_conversation_state" && e.tool_args) {
    const args = e.tool_args as { field?: string; value?: unknown };
    return `set ${args.field ?? "?"} = ${formatValue(args.value)}`;
  }
  if (e.tool_name === "lookup_relevant_rules" && e.tool_args) {
    const t = (e.tool_args as { tool_name?: string }).tool_name;
    return `looked up rules for ${t}`;
  }
  if (e.tool_name === "request_information" && e.tool_args) {
    const fields = (e.tool_args as { fields?: string[] }).fields || [];
    return `asked for ${fields.join(", ")}`;
  }
  if (e.tool_name === "escalate_to_human" && e.tool_args) {
    const reason = (e.tool_args as { reason?: string }).reason || "(no reason)";
    return `escalating: ${reason}`;
  }
  if (e.user_facing_message) return e.user_facing_message;
  if (e.tool_name && e.tool_args) {
    const args = e.tool_args as Record<string, unknown>;
    const compact = Object.entries(args)
      .slice(0, 3)
      .map(([k, v]) => `${k}=${formatValue(v)}`)
      .join(", ");
    return compact || null;
  }
  return null;
}

function detailLines(e: AuditEvent): [string, string][] {
  const out: [string, string][] = [];
  if (e.tool_args) {
    for (const [k, v] of Object.entries(e.tool_args as Record<string, unknown>)) {
      out.push([k, formatValue(v)]);
    }
  }
  if (e.proposed_action) {
    for (const [k, v] of Object.entries(e.proposed_action as Record<string, unknown>)) {
      if (k === "action") continue;
      out.push([`proposed.${k}`, formatValue(v)]);
    }
  }
  return out;
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return String(v);
  if (typeof v === "string") return v.length > 80 ? v.slice(0, 77) + "…" : v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    const s = JSON.stringify(v);
    return s.length > 120 ? s.slice(0, 117) + "…" : s;
  } catch {
    return String(v);
  }
}