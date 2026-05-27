"use client";

import { useEffect, useRef, useState } from "react";
import { api, type AuditEvent, type Conversation } from "@/lib/api";
import { readSSE } from "@/lib/sse";
import { MessageBubble } from "@/components/MessageBubble";
import { LiveActivityRail } from "@/components/LiveActivityRail";
import { cn } from "@/lib/cn";
import { RotateCcw, Send, Loader2 } from "lucide-react";

type StreamItem = {
  kind: "msg";
  role: "user" | "assistant";
  content: string;
  id: string;
};

const STORAGE_KEY = (businessId: string) => `guardrails:conv:${businessId}`;

export function ChatPanel({ businessId }: { businessId: string }) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [items, setItems] = useState<StreamItem[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Load or create a conversation for this business.
  useEffect(() => {
    if (!businessId) return;
    const cached = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY(businessId)) : null;
    const init = async () => {
      try {
        if (cached) {
          const c = await api.conversations.get(cached);
          setConversation(c);
          const msgs = await api.conversations.listMessages(c.id);
          setItems(
            msgs.map((m) => ({ kind: "msg", role: m.role, content: m.content, id: m.id })),
          );
          const events = await api.conversations.events(c.id);
          setAuditEvents(events);
          return;
        }
        const c = await api.conversations.create(businessId);
        localStorage.setItem(STORAGE_KEY(businessId), c.id);
        setConversation(c);
        setItems([]);
        setAuditEvents([]);
      } catch (e) {
        if (cached) {
          localStorage.removeItem(STORAGE_KEY(businessId));
          const c = await api.conversations.create(businessId);
          localStorage.setItem(STORAGE_KEY(businessId), c.id);
          setConversation(c);
          setItems([]);
          setAuditEvents([]);
        } else {
          setError(String(e));
        }
      }
    };
    init();
  }, [businessId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    // Tracking the last item's id (rather than the array length) means we
    // scroll exactly once per genuinely-new message, not on every re-render
    // where the items array is rebuilt with the same content.
  }, [items[items.length - 1]?.id, streaming]);

  // While the agent is streaming, poll the events endpoint every 1.5s so the
  // Live activity rail updates as tool calls happen, not just at the end.
  useEffect(() => {
    if (!streaming || !conversation) return;
    const id = window.setInterval(async () => {
      try {
        const events = await api.conversations.events(conversation.id);
        setAuditEvents(events);
      } catch {
        /* ignore transient errors during streaming */
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, [streaming, conversation]);

  const send = async () => {
    if (!conversation || !draft.trim() || streaming) return;
    const text = draft.trim();
    setDraft("");
    setStreaming(true);
    setError(null);
    setItems((prev) => [
      ...prev,
      { kind: "msg", role: "user", content: text, id: `u-${Date.now()}` },
      { kind: "msg", role: "assistant", content: "", id: `a-${Date.now()}` },
    ]);

    try {
      const res = await api.conversations.streamMessage(conversation.id, text);
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`${res.status} ${body || res.statusText}`);
      }
      for await (const ev of readSSE(res)) {
        if (ev.event === "message_chunk") {
          const data = JSON.parse(ev.data) as { text?: string };
          const piece = data.text ?? "";
          setItems((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.kind === "msg" && last.role === "assistant") {
              next[next.length - 1] = { ...last, content: last.content + piece };
            }
            return next;
          });
        } else if (ev.event === "done") {
          // final message text already streamed; nothing to append.
        } else if (ev.event === "error") {
          const data = JSON.parse(ev.data) as { message?: string };
          setError(data.message || "stream error");
        }
      }
      // Refresh audit events panel
      const events = await api.conversations.events(conversation.id);
      setAuditEvents(events);
    } catch (e) {
      setError(String(e));
    } finally {
      setStreaming(false);
    }
  };

  const reset = async () => {
    if (!conversation) return;
    await api.conversations.reset(conversation.id);
    setItems([]);
    setAuditEvents([]);
    setError(null);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-[1fr_320px] gap-4 h-[calc(100vh-200px)] min-h-[520px]">
      <section className="rounded-[var(--radius-lg)] border border-border bg-bg-elevated flex flex-col overflow-hidden">
        <header className="px-4 py-3 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="size-7 rounded-full bg-accent-tint text-accent grid place-items-center text-xs font-semibold">
              A
            </span>
            <div>
              <div className="text-sm font-medium text-ink">Customer-service agent</div>
              <div className="text-xs text-accent flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-accent" /> Live
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={reset}
            className="text-xs text-ink-muted hover:text-ink inline-flex items-center gap-1"
          >
            <RotateCcw className="size-3" /> Reset
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {!conversation ? (
            <div className="grid place-items-center h-full text-ink-muted text-sm">
              Loading conversation…
            </div>
          ) : (
            <>
              {items.length === 0 && (
                <div className="text-center text-ink-muted text-sm py-12">
                  Try “Can I book HVAC service Sunday afternoon?” or “Hi, my AC is leaking, can someone come tonight?”
                </div>
              )}
              {items.map((it) => (
                <MessageBubble key={it.id} role={it.role} content={it.content || (streaming ? "…" : "")} />
              ))}
              {error && (
                <div className="rounded-md border border-rose/40 bg-rose-tint text-rose p-2 text-sm">
                  {error}
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
        <footer className="border-t border-border p-3 flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Message the agent…"
            rows={1}
            disabled={!conversation}
            className="flex-1 resize-none rounded-md border border-border bg-bg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 max-h-[120px] overflow-y-auto disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            disabled={!draft.trim() || streaming || !conversation}
            className={cn(
              "size-9 grid place-items-center rounded-md bg-ink text-bg-elevated hover:bg-ink-soft",
              (!draft.trim() || streaming) && "opacity-50",
            )}
          >
            {streaming ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </button>
        </footer>
      </section>

      <LiveActivityRail events={auditEvents} streaming={streaming} />
    </div>
  );
}
