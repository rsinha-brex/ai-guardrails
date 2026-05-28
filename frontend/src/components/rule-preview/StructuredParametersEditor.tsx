"use client";

import { useId } from "react";

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
type Weekday = (typeof WEEKDAYS)[number];
type HoursMap = Partial<Record<Weekday, { start: string; end: string }>>;

type Params = Record<string, unknown>;

type Props = {
  ruleType: string;
  parameters: Params;
  onChange: (next: Params) => void;
};

/**
 * Per-rule-type structured editor. Renders form widgets matching the
 * shape of each rule's parameters object, keeps the parameters dict
 * in sync via `onChange` on every keystroke / toggle.
 *
 * For rule types we don't have a dedicated editor for (`conditional_block`)
 * we fall back to a JSON textarea so the owner still has a way through.
 */
export function StructuredParametersEditor({ ruleType, parameters, onChange }: Props) {
  switch (ruleType) {
    case "business_hours":
      return <BusinessHoursEditor parameters={parameters} onChange={onChange} />;
    case "service_area_zip":
      return <ServiceAreaEditor parameters={parameters} onChange={onChange} />;
    case "services_offered":
      return <ServicesOfferedEditor parameters={parameters} onChange={onChange} />;
    case "customer_eligibility":
      return <CustomerEligibilityEditor parameters={parameters} onChange={onChange} />;
    case "lead_time_minimum":
      return <LeadTimeEditor parameters={parameters} onChange={onChange} />;
    case "output_constraint":
      return <OutputConstraintEditor parameters={parameters} onChange={onChange} />;
    case "conditional_block":
    default:
      return <JsonEditor parameters={parameters} onChange={onChange} />;
  }
}

// --------------------------------------------------------------------------- //
// Shared layout primitives
// --------------------------------------------------------------------------- //

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-mono text-[10px] uppercase tracking-widest text-ink-faint mb-1">
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full bg-bg-elevated border border-border rounded-md px-2 py-1.5 text-sm text-ink-soft focus:outline-none focus:border-accent/40";

const textareaClass = inputClass + " resize-none font-mono text-xs";

// --------------------------------------------------------------------------- //
// business_hours
// --------------------------------------------------------------------------- //

function BusinessHoursEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const tz = String(parameters.timezone ?? "America/New_York");
  const hours = (parameters.hours_by_day as HoursMap) || {};
  const closedDays = (parameters.closed_days as Weekday[]) || [];
  const blockMessage = String(parameters.block_message ?? "");

  const setDay = (day: Weekday, range: { start: string; end: string } | null) => {
    const nextHours = { ...hours };
    if (range === null) delete nextHours[day];
    else nextHours[day] = range;
    onChange({ ...parameters, hours_by_day: nextHours });
  };

  const toggleClosed = (day: Weekday) => {
    const next = closedDays.includes(day)
      ? closedDays.filter((d) => d !== day)
      : [...closedDays, day];
    onChange({ ...parameters, closed_days: next });
  };

  return (
    <div className="space-y-3">
      <Field label="timezone">
        <input
          type="text"
          value={tz}
          onChange={(e) => onChange({ ...parameters, timezone: e.target.value })}
          className={inputClass}
        />
      </Field>
      <div className="space-y-1">
        <Label>weekly hours</Label>
        {closedDays.length > 0 && (
          <div className="text-xs text-ink-muted -mt-0.5 mb-1.5">
            Closed:{" "}
            <span className="font-mono uppercase tracking-wide text-ink-soft">
              {closedDays
                .slice()
                .sort((a, b) => WEEKDAYS.indexOf(a) - WEEKDAYS.indexOf(b))
                .join(", ")}
            </span>
          </div>
        )}
        <div className="rounded-md border border-border overflow-hidden divide-y divide-border">
          {WEEKDAYS.map((day) => {
            const range = hours[day];
            const isClosed = closedDays.includes(day);
            return (
              <div
                key={day}
                className={
                  "flex items-center gap-2 px-3 py-2 " +
                  (isClosed ? "bg-bg-subtle" : "bg-bg-elevated")
                }
              >
                <div className="w-10 text-xs font-mono uppercase text-ink-muted">{day}</div>
                <label
                  className={
                    "text-xs flex items-center gap-1 cursor-pointer " +
                    (isClosed ? "text-ink-soft font-medium" : "text-ink-muted")
                  }
                >
                  <input
                    type="checkbox"
                    checked={isClosed}
                    onChange={() => toggleClosed(day)}
                  />
                  closed
                </label>
                {!isClosed && (
                  <>
                    <input
                      type="time"
                      value={range?.start || "09:00"}
                      onChange={(e) =>
                        setDay(day, { start: e.target.value, end: range?.end || "17:00" })
                      }
                      className="rounded border border-border bg-bg px-2 py-1 text-xs text-ink-soft"
                    />
                    <span className="text-ink-muted text-xs">–</span>
                    <input
                      type="time"
                      value={range?.end || "17:00"}
                      onChange={(e) =>
                        setDay(day, { start: range?.start || "09:00", end: e.target.value })
                      }
                      className="rounded border border-border bg-bg px-2 py-1 text-xs text-ink-soft"
                    />
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <Field label="block message">
        <textarea
          value={blockMessage}
          rows={2}
          onChange={(e) => onChange({ ...parameters, block_message: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// service_area_zip
// --------------------------------------------------------------------------- //

function ServiceAreaEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const allowed = (parameters.allowed_zips as string[]) || [];
  const denied = (parameters.denied_zips as string[]) || [];
  const blockMessage = String(parameters.block_message ?? "");

  return (
    <div className="space-y-3">
      <Field label="allowed ZIPs (comma-separated)">
        <textarea
          value={allowed.join(", ")}
          rows={3}
          onChange={(e) =>
            onChange({
              ...parameters,
              allowed_zips: splitCsv(e.target.value),
            })
          }
          className={textareaClass}
        />
      </Field>
      <Field label="denied ZIPs (comma-separated, optional)">
        <textarea
          value={denied.join(", ")}
          rows={2}
          onChange={(e) =>
            onChange({
              ...parameters,
              denied_zips: splitCsv(e.target.value),
            })
          }
          className={textareaClass}
        />
      </Field>
      <Field label="block message">
        <textarea
          value={blockMessage}
          rows={2}
          onChange={(e) => onChange({ ...parameters, block_message: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// services_offered
// --------------------------------------------------------------------------- //

function ServicesOfferedEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const allowed = (parameters.allowed_services as string[]) || [];
  const blockMessage = String(parameters.block_message ?? "");

  return (
    <div className="space-y-3">
      <Field label="allowed services (comma-separated)">
        <textarea
          value={allowed.join(", ")}
          rows={3}
          onChange={(e) =>
            onChange({
              ...parameters,
              allowed_services: splitCsv(e.target.value),
            })
          }
          className={textareaClass}
        />
      </Field>
      <Field label="block message">
        <textarea
          value={blockMessage}
          rows={2}
          onChange={(e) => onChange({ ...parameters, block_message: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// customer_eligibility
// --------------------------------------------------------------------------- //

function CustomerEligibilityEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const homeowner = !!parameters.homeowner_required;
  const excludeRenters = !!parameters.exclude_renters;
  const membership = !!parameters.membership_required;
  const fields = (parameters.required_state_fields as string[]) || [];
  const blockMessage = String(parameters.block_message ?? "");

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <Label>gates</Label>
        <div className="space-y-1.5">
          <Toggle
            checked={homeowner}
            onChange={(v) => onChange({ ...parameters, homeowner_required: v })}
            label="Homeowner required"
          />
          <Toggle
            checked={excludeRenters}
            onChange={(v) => onChange({ ...parameters, exclude_renters: v })}
            label="Exclude renters"
          />
          <Toggle
            checked={membership}
            onChange={(v) => onChange({ ...parameters, membership_required: v })}
            label="Membership required"
          />
        </div>
      </div>
      <Field label="required state fields (comma-separated)">
        <textarea
          value={fields.join(", ")}
          rows={2}
          onChange={(e) =>
            onChange({
              ...parameters,
              required_state_fields: splitCsv(e.target.value),
            })
          }
          className={textareaClass}
        />
      </Field>
      <Field label="block message">
        <textarea
          value={blockMessage}
          rows={2}
          onChange={(e) => onChange({ ...parameters, block_message: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// lead_time_minimum
// --------------------------------------------------------------------------- //

function LeadTimeEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const hours = Number(parameters.minimum_hours ?? 0);
  const services = (parameters.applies_to_service_types as string[] | null) || [];
  const bypassField = String(parameters.bypass_if_state_field ?? "");
  const bypassValue = parameters.bypass_if_state_value;
  const blockMessage = String(parameters.block_message ?? "");

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Field label="minimum hours">
          <input
            type="number"
            min={0}
            value={hours}
            onChange={(e) =>
              onChange({ ...parameters, minimum_hours: parseInt(e.target.value, 10) || 0 })
            }
            className={inputClass}
          />
        </Field>
        <Field label="applies to (comma-separated, blank = all)">
          <input
            type="text"
            value={services.join(", ")}
            onChange={(e) => {
              const list = splitCsv(e.target.value);
              onChange({
                ...parameters,
                applies_to_service_types: list.length ? list : null,
              });
            }}
            className={inputClass}
          />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="bypass when state field…">
          <input
            type="text"
            value={bypassField}
            placeholder="(optional)"
            onChange={(e) =>
              onChange({
                ...parameters,
                bypass_if_state_field: e.target.value || null,
              })
            }
            className={inputClass}
          />
        </Field>
        <Field label="…equals">
          <input
            type="text"
            value={bypassValue === undefined || bypassValue === null ? "" : String(bypassValue)}
            placeholder="true / false / value"
            onChange={(e) => {
              const raw = e.target.value;
              let parsed: unknown = raw;
              if (raw === "true") parsed = true;
              else if (raw === "false") parsed = false;
              else if (raw === "") parsed = null;
              else if (!isNaN(Number(raw))) parsed = Number(raw);
              onChange({ ...parameters, bypass_if_state_value: parsed });
            }}
            className={inputClass}
          />
        </Field>
      </div>
      <Field label="block message">
        <textarea
          value={blockMessage}
          rows={2}
          onChange={(e) => onChange({ ...parameters, block_message: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// output_constraint
// --------------------------------------------------------------------------- //

function OutputConstraintEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  const instruction = String(parameters.instruction ?? "");
  const severity = String(parameters.severity ?? "guidance");
  const id = useId();

  return (
    <div className="space-y-3">
      <Field label="instruction">
        <textarea
          value={instruction}
          rows={4}
          onChange={(e) => onChange({ ...parameters, instruction: e.target.value })}
          className={inputClass + " resize-none"}
        />
      </Field>
      <Field label="severity">
        <div className="flex gap-3 text-sm">
          {["guidance", "must"].map((s) => (
            <label key={s} className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name={id}
                checked={severity === s}
                onChange={() => onChange({ ...parameters, severity: s })}
              />
              {s}
            </label>
          ))}
        </div>
      </Field>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// JSON fallback (conditional_block + anything unrecognized)
// --------------------------------------------------------------------------- //

function JsonEditor({ parameters, onChange }: { parameters: Params; onChange: (p: Params) => void }) {
  return (
    <Field label="raw parameters (JSON)">
      <textarea
        defaultValue={JSON.stringify(parameters, null, 2)}
        rows={14}
        onChange={(e) => {
          try {
            const next = JSON.parse(e.target.value);
            if (next && typeof next === "object") onChange(next as Params);
          } catch {
            // ignore parse errors mid-typing — owner will see the JSON they
            // typed until it parses cleanly again
          }
        }}
        className={textareaClass}
      />
    </Field>
  );
}

// --------------------------------------------------------------------------- //
// Bits
// --------------------------------------------------------------------------- //

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-ink-soft cursor-pointer">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

function splitCsv(s: string): string[] {
  return s
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}
