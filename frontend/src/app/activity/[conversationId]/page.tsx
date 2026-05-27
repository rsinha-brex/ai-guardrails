"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api, type DrillInResponse } from "@/lib/api";
import { cn } from "@/lib/cn";
import { ArrowLeft, FileText, X } from "lucide-react";

import { STATUS_PILL_CLASS, statusKeyOr } from "@/lib/status-styles";

const OUTCOME_BG = STATUS_PILL_CLASS;

export default function ConversationDrillIn({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = use(params);
  const [data, setData] = useState<DrillInResponse | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.conversations
      .drill(conversationId)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [conversationId]);

  if (error)
    return (
      <AppShell>
        <div className="rounded-md border border-rose/40 bg-rose-tint p-4 text-rose text-sm">
          {error}
        </div>
      </AppShell>
    );

  if (!data)
    return (
      <AppShell>
        <div className="text-ink-muted text-sm">Loading…</div>
      </AppShell>
    );

  // Interleave events + messages by timestamp for a unified timeline.
  type Item =
    | {
        kind: "event";
        at: string;
        eventType: string;
        outcome: string;
        toolName: string | null;
        ruleName: string | null;
        userMsg: string | null;
        internal: string | null;
        toolArgs: Record<string, unknown> | null;
        id: string;
      }
    | {
        kind: "message";
        at: string;
        role: string;
        content: string;
        id: string;
      };

  const items: Item[] = [
    ...data.messages.map<Item>((m) => ({
      kind: "message",
      at: m.created_at,
      role: m.role,
      content: m.content,
      id: m.id,
    })),
    ...data.events.map<Item>((e) => ({
      kind: "event",
      at: e.fired_at,
      eventType: e.event_type,
      outcome: e.outcome,
      toolName: e.tool_name,
      ruleName: e.fired_rule_name,
      userMsg: e.user_facing_message,
      internal: e.internal_reason,
      toolArgs: e.tool_args,
      id: e.id,
    })),
  ].sort((a, b) => a.at.localeCompare(b.at));

  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-2">
        <Link
          href={`/activity?business=${data.conversation.business_id}`}
          className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink"
        >
          <ArrowLeft className="size-3" /> Activity
        </Link>
      </div>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">
            Conversation with {data.conversation.customer_identifier}
          </h1>
          <p className="text-ink-muted mt-1 text-sm">
            {data.events.length} events · {data.messages.length} messages
            {data.conversation.is_test && " · test conversation"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPrompt(true)}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-bg-elevated px-2.5 py-1.5 text-xs hover:border-border-strong"
        >
          <FileText className="size-3.5" />
          Show agent context
        </button>
      </div>

      <div className="max-h-[calc(100vh-220px)] overflow-y-auto pr-2 -mr-2">
        <ol className="relative pl-5 border-l border-border space-y-3">
        {items.map((it) => (
          <li key={it.id} className="relative">
            <span className="absolute -left-[7px] top-2 size-2.5 rounded-full bg-bg-elevated border border-border-strong" />
            {it.kind === "message" ? (
              <div className="rounded-[var(--radius)] border border-border bg-bg-elevated p-3">
                <div className="text-[11px] font-mono uppercase tracking-widest text-ink-muted mb-1">
                  {it.role} · {new Date(it.at).toLocaleTimeString()}
                </div>
                <div className="text-sm text-ink">{it.content}</div>
              </div>
            ) : (
              <div
                className={cn(
                  "rounded-[var(--radius)] border p-3",
                  it.outcome ? OUTCOME_BG[statusKeyOr(it.outcome)] : "bg-bg-elevated border-border",
                )}
              >
                <div className="text-[11px] font-mono uppercase tracking-widest mb-1 opacity-80">
                  {it.eventType} · {it.outcome} · {new Date(it.at).toLocaleTimeString()}
                </div>
                <div className="text-sm">
                  <span className="font-medium">{it.toolName}</span>
                  {it.ruleName && <span className="opacity-80"> — rule “{it.ruleName}”</span>}
                </div>
                {it.userMsg && <div className="text-xs italic mt-1 opacity-90">"{it.userMsg}"</div>}
                {it.internal && (
                  <div className="text-xs mt-1 opacity-70 font-mono">{it.internal}</div>
                )}
                {it.toolArgs && Object.keys(it.toolArgs).length > 0 && (
                  <details className="mt-1">
                    <summary className="text-xs cursor-pointer opacity-70">args</summary>
                    <pre className="mt-1 rounded bg-ink/5 p-2 text-[11px] font-mono overflow-auto max-h-[50vh]">
                      {JSON.stringify(it.toolArgs, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </li>
        ))}
        </ol>
      </div>

      {showPrompt && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-ink/30 p-6"
          onClick={() => setShowPrompt(false)}
        >
          <div
            className="w-full max-w-3xl rounded-[var(--radius-lg)] bg-bg-elevated shadow-lg overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="font-display text-lg">Agent context at conversation start</h3>
              <button
                type="button"
                onClick={() => setShowPrompt(false)}
                className="size-8 grid place-items-center rounded-md hover:bg-bg-subtle text-ink-muted"
              >
                <X className="size-4" />
              </button>
            </div>
            <pre className="p-5 overflow-auto max-h-[70vh] text-[11px] font-mono whitespace-pre-wrap text-ink-soft">
              {data.system_prompt || "(no snapshot)"}
            </pre>
          </div>
        </div>
      )}
    </AppShell>
  );
}
