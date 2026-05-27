/**
 * Single source of truth for status / outcome visual treatments.
 *
 * The rule engine emits four canonical outcomes — `accepted | blocked |
 * needs_info | info` — plus `failed` (tool error) and `open` (a conversation
 * that hasn't yet hit a terminal outcome). UI components share the same
 * palette / labels rather than each defining their own — keeps the design
 * tight and lets a single edit retune every status pill across the app.
 */

export type StatusKey =
  | "accepted"
  | "blocked"
  | "needs_info"
  | "info"
  | "failed"
  | "open";

/** Pill background + text + border classes. */
export const STATUS_PILL_CLASS: Record<StatusKey, string> = {
  accepted: "bg-accent-tint text-accent border-accent/30",
  blocked: "bg-rose-tint text-rose border-rose/30",
  needs_info: "bg-amber-tint text-amber border-amber/30",
  info: "bg-bg-subtle text-ink-soft border-border",
  failed: "bg-rose-tint text-rose border-rose/30",
  open: "bg-bg-subtle text-ink-muted border-border",
};

/** Small dot color (used in compact list rows). */
export const STATUS_DOT_CLASS: Record<StatusKey, string> = {
  accepted: "bg-accent",
  blocked: "bg-rose",
  needs_info: "bg-amber",
  info: "bg-ink-faint",
  failed: "bg-rose",
  open: "bg-ink-faint",
};

/** Sentence-case human label. */
export const STATUS_LABEL: Record<StatusKey, string> = {
  accepted: "Allowed",
  blocked: "Blocked",
  needs_info: "Needs info",
  info: "Info",
  failed: "Failed",
  open: "Open",
};

/** All-caps mono-style label, used in the Live activity rail and audit chips. */
export const STATUS_LABEL_UPPER: Record<StatusKey, string> = {
  accepted: "ALLOWED",
  blocked: "BLOCKED",
  needs_info: "NEEDS INFO",
  info: "INFO",
  failed: "FAILED",
  open: "OPEN",
};

/**
 * Look up by string with a fallback to the `info` treatment for unknown
 * outcomes — the engine's typed union covers the canonical set, but audit
 * rows occasionally carry custom strings (e.g. `lookup`).
 */
export function statusKeyOr(s: string, fallback: StatusKey = "info"): StatusKey {
  return (s in STATUS_PILL_CLASS ? (s as StatusKey) : fallback);
}
