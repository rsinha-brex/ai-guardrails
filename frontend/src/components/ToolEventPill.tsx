"use client";

import { cn } from "@/lib/cn";
import { Loader2, Ban, CheckCircle2, ArrowRight } from "lucide-react";

export type ToolEvent = {
  id: string;
  tool: string;
  status: "pending" | "accepted" | "blocked" | "needs_info" | "info";
  detail?: string;
  ruleName?: string;
};

const STATUS_STYLE: Record<ToolEvent["status"], string> = {
  pending: "bg-bg-subtle text-ink-muted border-border",
  accepted: "bg-accent-tint text-accent border-accent/30",
  blocked: "bg-rose-tint text-rose border-rose/30",
  needs_info: "bg-amber-tint text-amber border-amber/30",
  info: "bg-bg-subtle text-ink-soft border-border",
};

const STATUS_ICON: Record<ToolEvent["status"], React.ReactNode> = {
  pending: <Loader2 className="size-3 animate-spin" />,
  accepted: <CheckCircle2 className="size-3" />,
  blocked: <Ban className="size-3" />,
  needs_info: <ArrowRight className="size-3" />,
  info: <ArrowRight className="size-3" />,
};

export function ToolEventPill({ event }: { event: ToolEvent }) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-mono",
        STATUS_STYLE[event.status],
      )}
    >
      {STATUS_ICON[event.status]}
      <span className="font-medium">{event.tool}</span>
      {event.ruleName ? <span className="opacity-80">· {event.ruleName}</span> : null}
      {event.detail ? <span className="opacity-80">— {event.detail}</span> : null}
    </div>
  );
}
