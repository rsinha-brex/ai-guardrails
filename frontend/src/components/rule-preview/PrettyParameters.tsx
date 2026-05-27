"use client";

import { formatParameters } from "./format";

type Props = {
  ruleType: string;
  parameters: Record<string, unknown>;
  blockMessage?: string;
  onBlockMessageChange?: (v: string) => void;
  instruction?: string;
  onInstructionChange?: (v: string) => void;
};

/**
 * Definition-list view of compiled rule parameters with inline-editable
 * `block_message` and `instruction` fields. Read-only fields are formatted
 * by `formatParameters`; the two editable fields are rendered separately
 * so they're discoverable to the owner.
 */
export function PrettyParameters({
  ruleType,
  parameters,
  blockMessage,
  onBlockMessageChange,
  instruction,
  onInstructionChange,
}: Props) {
  const rows = formatParameters(ruleType, parameters);
  // Strip block_message / instruction from the read-only rows; they get
  // editable widgets below.
  const readonlyRows = rows.filter(([k]) => k !== "block message" && k !== "instruction");

  return (
    <dl className="rounded-md border border-accent/30 bg-bg-elevated/70 px-3 py-2 text-sm grid grid-cols-[140px_1fr] gap-x-3 gap-y-2">
      {readonlyRows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-ink-muted font-mono text-[11px] uppercase tracking-wider self-center">
            {k}
          </dt>
          <dd className="text-ink-soft break-words">{v}</dd>
        </div>
      ))}
      {onBlockMessageChange && blockMessage !== undefined && (
        <div className="contents">
          <dt className="text-ink-muted font-mono text-[11px] uppercase tracking-wider self-start pt-2">
            block message
          </dt>
          <dd>
            <textarea
              value={blockMessage}
              rows={2}
              onChange={(e) => onBlockMessageChange(e.target.value)}
              className="w-full bg-bg-elevated border border-border rounded-md px-2 py-1.5 text-ink-soft text-sm resize-none focus:outline-none focus:border-accent/40"
            />
          </dd>
        </div>
      )}
      {onInstructionChange && instruction !== undefined && (
        <div className="contents">
          <dt className="text-ink-muted font-mono text-[11px] uppercase tracking-wider self-start pt-2">
            instruction
          </dt>
          <dd>
            <textarea
              value={instruction}
              rows={2}
              onChange={(e) => onInstructionChange(e.target.value)}
              className="w-full bg-bg-elevated border border-border rounded-md px-2 py-1.5 text-ink-soft text-sm resize-none focus:outline-none focus:border-accent/40"
            />
          </dd>
        </div>
      )}
    </dl>
  );
}
