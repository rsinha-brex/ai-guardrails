"use client";

import { cn } from "@/lib/cn";

type Props = {
  label: string;
  value: string;
  onChange: (v: string) => void;
  as: "input" | "textarea";
  rows?: number;
  className?: string;
};

/**
 * Inline-editable text field with a small uppercase label above it. Used in
 * the compiled-rule preview for the editable "rule name", "description",
 * "applies when" fields. Looks like a label/value pair when not focused;
 * looks like a form field when focused.
 */
export function EditableField({ label, value, onChange, as, rows, className }: Props) {
  const baseClass = cn(
    "w-full bg-transparent border border-transparent rounded-md px-2 py-1.5 -mx-2 -my-1.5",
    "hover:bg-bg-elevated/60 focus:bg-bg-elevated focus:border-accent/40 focus:outline-none transition-colors",
    "resize-none",
    className,
  );
  return (
    <div className="space-y-0.5">
      <div className="font-mono text-[10px] uppercase tracking-widest text-ink-faint">{label}</div>
      {as === "input" ? (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={baseClass}
        />
      ) : (
        <textarea
          value={value}
          rows={rows ?? 2}
          onChange={(e) => onChange(e.target.value)}
          className={baseClass}
        />
      )}
    </div>
  );
}
