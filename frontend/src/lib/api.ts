/**
 * Typed wrappers around the FastAPI surface, going through /api/proxy.
 */
export type Business = {
  id: string;
  name: string;
  timezone: string;
  description: string;
};

export type RuleSummary = {
  id: string;
  business_id: string;
  rule_type: string;
  name: string;
  description: string;
  applies_when_description: string;
  parameters: Record<string, unknown>;
  applies_to_tools: string[];
  enforcement_mode: string;
  priority: number;
  is_active: boolean;
  source_prompt: string | null;
  test_case_count: number;
  test_passing: number;
  test_failing: number;
};

export type CompiledRule = {
  rule_type: string;
  name: string;
  description: string;
  applies_when_description: string;
  applies_to_tools: string[];
  enforcement_mode: string;
  priority: number;
  parameters: RuleParameters;
  source_prompt: string;
  rationale: string;
  confidence?: "concrete" | "draft";
  draft_gaps?: string[];
};

/**
 * Per-rule-type parameter shapes, mirroring `app/schemas/rules.py`. The
 * union is partially open (extras allowed) because the compile step
 * occasionally produces extra fields for newer rule types — we don't want
 * UI editors to break on field additions before the type is updated here.
 */
export type RuleParameters =
  | BusinessHoursParameters
  | ServiceAreaZipParameters
  | ServicesOfferedParameters
  | CustomerEligibilityParameters
  | LeadTimeMinimumParameters
  | ConditionalBlockParameters
  | OutputConstraintParameters
  | Record<string, unknown>;

export type BusinessHoursParameters = {
  timezone: string;
  hours_by_day: Record<string, { start: string; end: string }>;
  closed_days: string[];
  block_message: string;
};

export type ServiceAreaZipParameters = {
  allowed_zips: string[];
  denied_zips: string[];
  block_message: string;
};

export type ServicesOfferedParameters = {
  allowed_services: string[];
  block_message: string;
};

export type CustomerEligibilityParameters = {
  homeowner_required: boolean;
  exclude_renters: boolean;
  membership_required: boolean;
  block_message: string;
  required_state_fields: string[];
  applies_to_service_types?: string[] | null;
};

export type LeadTimeMinimumParameters = {
  minimum_hours: number;
  applies_to_service_types?: string[] | null;
  bypass_if_state_field?: string | null;
  bypass_if_state_value?: unknown;
  block_message: string;
};

export type ConditionalBlockParameters = {
  trigger: Record<string, unknown>;
  required_precondition?: Record<string, unknown> | null;
  block_message: string;
};

export type OutputConstraintParameters = {
  instruction: string;
  severity?: "guidance" | "must";
};

/**
 * Read a string field from RuleParameters with a default. The discriminated
 * union types above guarantee the field exists for the right rule_type;
 * this helper handles the open-`Record` fallback case without scattering
 * `as` casts at every read site.
 */
export function paramString(p: RuleParameters, key: string): string | undefined {
  const v = (p as Record<string, unknown>)[key];
  return typeof v === "string" ? v : undefined;
}

export type CompileFailure = {
  suggested_clarifications: string[];
  rationale: string;
};

export type CompileResult =
  | { kind: "compiled"; rule: CompiledRule; failure: null }
  | { kind: "failure"; rule: null; failure: CompileFailure };

export type Conversation = {
  id: string;
  business_id: string;
  customer_identifier: string;
  state: Record<string, unknown>;
  started_at: string;
  last_message_at: string;
  message_count: number;
  had_blocked_action: boolean;
  had_accepted_action: boolean;
  blocked_rule_ids: string[];
  is_test: boolean;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  business_id: string;
  customer_identifier: string;
  started_at: string;
  last_message_at: string;
  message_count: number;
  had_blocked_action: boolean;
  had_accepted_action: boolean;
  blocked_rule_ids: string[];
  is_test: boolean;
  outcome: "blocked" | "accepted" | "open";
};

export type AuditEvent = {
  id: string;
  event_type: string;
  outcome: string;
  tool_name: string | null;
  fired_rule_id: string | null;
  fired_rule_type: string | null;
  fired_rule_name: string | null;
  tool_args: Record<string, unknown> | null;
  proposed_action: Record<string, unknown> | null;
  user_facing_message: string | null;
  internal_reason: string | null;
  required_fields: string[] | null;
  fired_at: string;
};

export type DrillInResponse = {
  conversation: ConversationSummary;
  events: AuditEvent[];
  messages: ChatMessage[];
  system_prompt: string;
};

export type TestCase = {
  id: string;
  rule_id: string;
  customer_message: string;
  expected_outcome: "block" | "allow" | "needs_info";
  expected_notes: string | null;
  last_run_at: string | null;
  last_run_result: "pass" | "fail" | null;
  last_run_details: Record<string, unknown> | null;
};

export type RuleRefinement = {
  updated_prompt: string;
  explanation: string;
  diff_summary: string;
};

export type RefineResponse = {
  refinement: RuleRefinement;
  recompiled: CompiledRule | null;
  failure: CompileFailure | null;
};

const proxy = (path: string) => `/api/proxy${path}`;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(proxy(path), {
    headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  businesses: {
    list: () => request<Business[]>("/api/businesses"),
  },
  rules: {
    list: (businessId: string) =>
      request<RuleSummary[]>(`/api/businesses/${businessId}/rules`),
    create: (businessId: string, body: { compiled?: CompiledRule; prompt?: string }) =>
      request<{ rule: RuleSummary | null; failure: CompileFailure | null }>(
        `/api/businesses/${businessId}/rules`,
        { method: "POST", body: JSON.stringify(body) },
      ),
    compile: (businessId: string, prompt: string) =>
      request<CompileResult>(`/api/businesses/${businessId}/rules/compile`, {
        method: "POST",
        body: JSON.stringify({ prompt }),
      }),
    update: (businessId: string, ruleId: string, body: Partial<RuleSummary>) =>
      request<RuleSummary>(`/api/businesses/${businessId}/rules/${ruleId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    remove: (businessId: string, ruleId: string) =>
      request<{ deleted: string }>(
        `/api/businesses/${businessId}/rules/${ruleId}`,
        { method: "DELETE" },
      ),
  },
  conversations: {
    create: (businessId: string, customerIdentifier?: string, isTest = false) =>
      request<Conversation>(`/api/conversations`, {
        method: "POST",
        body: JSON.stringify({
          business_id: businessId,
          customer_identifier: customerIdentifier,
          is_test: isTest,
        }),
      }),
    get: (conversationId: string) =>
      request<Conversation>(`/api/conversations/${conversationId}`),
    listMessages: (conversationId: string) =>
      request<ChatMessage[]>(`/api/conversations/${conversationId}/messages`),
    reset: (conversationId: string) =>
      request<{ reset: string }>(`/api/conversations/${conversationId}`, { method: "DELETE" }),
    streamMessage: (conversationId: string, content: string) =>
      fetch(proxy(`/api/conversations/${conversationId}/messages`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }),
    events: (conversationId: string) =>
      request<AuditEvent[]>(`/api/conversations/${conversationId}/events`),
    drill: (conversationId: string) =>
      request<DrillInResponse>(`/api/conversations/${conversationId}/drill`),
  },
  activity: {
    list: (
      businessId: string,
      params: { outcome?: string; rule_id?: string; customer?: string } = {},
    ) => {
      const usp = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) if (v) usp.set(k, v);
      const q = usp.toString();
      return request<ConversationSummary[]>(
        `/api/businesses/${businessId}/conversations${q ? `?${q}` : ""}`,
      );
    },
  },
  testCases: {
    list: (ruleId: string) =>
      request<TestCase[]>(`/api/rules/${ruleId}/test-cases`),
    create: (ruleId: string, body: { customer_message: string; expected_outcome: string; expected_notes?: string }) =>
      request<TestCase>(`/api/rules/${ruleId}/test-cases`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    remove: (ruleId: string, testCaseId: string) =>
      request<{ deleted: string }>(`/api/rules/${ruleId}/test-cases/${testCaseId}`, {
        method: "DELETE",
      }),
    runOne: (ruleId: string, testCaseId: string) =>
      request<TestCase>(`/api/rules/${ruleId}/test-cases/${testCaseId}/run`, {
        method: "POST",
      }),
    runAll: (ruleId: string) =>
      request<TestCase[]>(`/api/rules/${ruleId}/test-cases/run`, {
        method: "POST",
      }),
    refine: (ruleId: string, testCaseId: string) =>
      request<RefineResponse>(`/api/rules/${ruleId}/refine`, {
        method: "POST",
        body: JSON.stringify({ test_case_id: testCaseId }),
      }),
  },
};
