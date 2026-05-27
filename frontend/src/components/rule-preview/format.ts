/**
 * Helpers for human-readable rendering of compiled rule parameters.
 *
 * `formatParameters` produces `[label, value]` rows for the per-rule-type
 * definition list. `summarizeExpression` walks a conditional_block trigger
 * tree and renders a compact prefix-ish form.
 */

export function formatParameters(
  ruleType: string,
  p: Record<string, unknown>,
): [string, string][] {
  const out: [string, string][] = [];
  const v = (key: string) => p[key];

  if (ruleType === "business_hours") {
    if (typeof v("timezone") === "string") out.push(["timezone", v("timezone") as string]);
    const hours = v("hours_by_day") as Record<string, { start: string; end: string }> | undefined;
    if (hours && typeof hours === "object") {
      const parts = Object.entries(hours).map(([d, r]) => `${d} ${r.start}–${r.end}`);
      out.push(["open", parts.join(", ") || "—"]);
    }
    const closed = v("closed_days") as string[] | undefined;
    if (Array.isArray(closed) && closed.length) out.push(["closed", closed.join(", ")]);
  } else if (ruleType === "service_area_zip") {
    const allowed = v("allowed_zips") as string[] | undefined;
    if (allowed)
      out.push([
        "allowed ZIPs",
        `${allowed.length} ZIPs (${allowed.slice(0, 4).join(", ")}${allowed.length > 4 ? "…" : ""})`,
      ]);
    const denied = v("denied_zips") as string[] | undefined;
    if (denied?.length) out.push(["denied ZIPs", denied.join(", ")]);
  } else if (ruleType === "services_offered") {
    const services = v("allowed_services") as string[] | undefined;
    if (services) out.push(["services", services.join(", ")]);
  } else if (ruleType === "customer_eligibility") {
    if (v("homeowner_required")) out.push(["homeowner", "required"]);
    if (v("exclude_renters")) out.push(["renters", "excluded"]);
    if (v("membership_required")) out.push(["membership", "required"]);
    const fields = v("required_state_fields") as string[] | undefined;
    if (fields?.length) out.push(["needs to know", fields.join(", ")]);
  } else if (ruleType === "lead_time_minimum") {
    if (typeof v("minimum_hours") === "number")
      out.push(["minimum lead time", `${v("minimum_hours")} hours`]);
    const services = v("applies_to_service_types") as string[] | null;
    out.push(["applies to", Array.isArray(services) ? services.join(", ") : "all services"]);
    if (v("bypass_if_state_field"))
      out.push([
        "bypass when",
        `${v("bypass_if_state_field")} = ${JSON.stringify(v("bypass_if_state_value"))}`,
      ]);
  } else if (ruleType === "conditional_block") {
    out.push(["trigger", summarizeExpression(v("trigger"))]);
    if (v("required_precondition"))
      out.push(["precondition", summarizeExpression(v("required_precondition"))]);
  } else if (ruleType === "output_constraint") {
    out.push(["instruction", String(v("instruction") ?? "—")]);
    out.push(["severity", String(v("severity") ?? "guidance")]);
  }

  if (typeof v("block_message") === "string" && v("block_message")) {
    out.push(["block message", v("block_message") as string]);
  }
  return out;
}

export function summarizeExpression(expr: unknown): string {
  if (!expr || typeof expr !== "object") return "—";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const e = expr as any;
  switch (e.op) {
    case "all_of":
      return `all of: ${(e.children || []).map(summarizeExpression).join("; ")}`;
    case "any_of":
      return `any of: ${(e.children || []).map(summarizeExpression).join("; ")}`;
    case "not":
      return `not (${summarizeExpression(e.child)})`;
    case "llm_judge":
      return `LLM judges \`${e.field}\`: "${e.question}"`;
    case "in":
    case "not_in":
      return `${e.field} ${e.op === "in" ? "is one of" : "isn't one of"} [${(e.value || []).join(", ")}]`;
    case "contains":
      return `${e.field} contains "${e.value}"`;
    case "matches_regex":
      return `${e.field} matches /${e.value}/`;
    default:
      return `${e.field} ${e.op} ${JSON.stringify(e.value)}`;
  }
}
