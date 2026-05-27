# AI Guardrails — 500-Test Corpus Results (run #1 baseline)

> **Note:** This is the **run #1 baseline** report, generated before the
> systemic fixes landed. It documents what surfaced from the initial pass,
> with FAIL rows that drove the Family A / B / C systemic moves. See
> `FAILURES.md` for the post-fix run-by-run delta and `BUGS.md` for the
> per-issue triage that came out of this run.

_Generated from `20260527T075656Z.jsonl` · 500 rows_

## Summary

| Severity | PASS | CAVEAT | FAIL | SKIP | Total |
| --- | --- | --- | --- | --- | --- |
| 🔴 red | 72 | 15 | 40 | 4 | 131 |
| 🟡 yellow | 195 | 13 | 102 | 45 | 355 |
| 🟢 green | 5 | 0 | 2 | 7 | 14 |
| **All** | **272** | **28** | **144** | **56** | **500** |

## Section 1A Templates (R-001..R-060)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-001 | 🔴 | `GEN` | ✅ PASS | M-F 9-5 | created: M-F 9-5 |
| R-002 | 🔴 | `GEN` | ⏭️ SKIP | Split shift (lunch closure) | SKIP-feature-not-shipped: split-shift form |
| R-003 | 🔴 | `GEN` | ✅ PASS | Mon-Fri 7-7 Sat 8-4 | created: Mon-Fri 7-7 Sat 8-4 |
| R-004 | 🔴 | `GEN` | ✅ PASS | Always open | created: Always open |
| R-005 | 🔴 | `GEN` | ✅ PASS | Permanently closed | created: Permanently closed |
| R-006 | 🟡 | `GEN` | ⏭️ SKIP | Inverted hours rejected | SKIP-feature-not-shipped: structured form validation |
| R-007 | 🟡 | `GEN` | ⏭️ SKIP | Invalid TZ rejected | SKIP-feature-not-shipped: timezone autocomplete |
| R-008 | 🟡 | `GEN` | ⏭️ SKIP | Overlapping ranges within day | SKIP-feature-not-shipped: split-shift form |
| R-009 | 🟡 | `GEN` | ⏭️ SKIP | Default TZ from business | SKIP-feature-not-shipped: structured form |
| R-010 | 🟡 | `GEN` | ❌ FAIL | R-010 seasonal hours | expected kind compiled, got failure |
| R-011 | 🟡 | `GEN` | ⏭️ SKIP | 25:00 rejected | SKIP-feature-not-shipped: structured form validation |
| R-012 | 🟡 | `GEN` | ✅ PASS | Custom block message | created: Custom block message |
| R-013 | 🟡 | `GEN` | ⏭️ SKIP | Empty block message | SKIP-feature-not-shipped: structured form validation |
| R-014 | 🟢 | `GEN` | ✅ PASS | Long block message | compiled to business_hours |
| R-015 | 🟢 | `GEN` | ✅ PASS | Emoji in message | compiled to business_hours |
| R-016 | 🔴 | `GEN` | ✅ PASS | 5-ZIP allow-list | compiled to service_area_zip |
| R-017 | 🔴 | `GEN` | ✅ PASS | 50-ZIP list | compiled to service_area_zip |
| R-018 | 🔴 | `GEN` | ❌ FAIL | Cascade Seattle | expected kind compiled, got failure |
| R-019 | 🟡 | `GEN` | ✅ PASS | Allow + deny | compiled to service_area_zip |
| R-020 | 🔴 | `GEN` | ✅ PASS | Invalid ZIP | compile-failure with 13 clarifications |
| R-021 | 🟡 | `GEN` | ✅ PASS | ZIP+4 | compiled to service_area_zip |
| R-022 | 🟡 | `GEN` | ✅ PASS | Duplicate ZIPs | compiled to service_area_zip |
| R-023 | 🟡 | `GEN` | ✅ PASS | Empty list | compile-failure with 13 clarifications |
| R-024 | 🟢 | `GEN` | ❌ FAIL | City-named area | expected kind compiled, got failure |
| R-025 | 🟡 | `GEN` | ✅ PASS | Mountain View Denver | compiled to service_area_zip |
| R-026 | 🟡 | `GEN` | ❌ FAIL | Atlantic Pool South FL | expected kind compiled, got failure |
| R-027 | 🟡 | `GEN` | ❌ FAIL | PrairieFence Twin Cities | expected kind compiled, got failure |
| R-028 | 🟡 | `GEN` | ❌ FAIL | Sunset Bath SoCal | expected kind compiled, got failure |
| R-029 | 🟡 | `GEN` | ⏭️ SKIP | Update area by adding ZIP | SKIP-feature-not-shipped: edit modal |
| R-030 | 🟡 | `GEN` | ⏭️ SKIP | Update area by removing ZIPs | SKIP-feature-not-shipped: edit modal |
| R-031 | 🔴 | `GEN` | ✅ PASS | HVAC scope | compiled to services_offered |
| R-032 | 🔴 | `GEN` | ✅ PASS | Multi-trade | compiled to services_offered |
| R-033 | 🔴 | `GEN` | ✅ PASS | Cascade plumbing | compiled to services_offered |
| R-034 | 🔴 | `GEN` | ✅ PASS | Roofing scope | compiled to services_offered |
| R-035 | 🟡 | `GEN` | ✅ PASS | Bath scope | compiled to services_offered |
| R-036 | 🟡 | `GEN` | ❌ FAIL | Fence scope | expected kind compiled, got failure |
| R-037 | 🟡 | `GEN` | ✅ PASS | Pool scope | compiled to services_offered |
| R-038 | 🟡 | `GEN` | ✅ PASS | Residential-only | compiled to customer_eligibility |
| R-039 | 🟡 | `GEN` | ✅ PASS | Block list | compiled to services_offered |
| R-040 | 🟡 | `GEN` | ❌ FAIL | Empty list | expected kind failure, got compiled |
| R-041 | 🟡 | `GEN` | ❌ FAIL | Unknown service type | expected kind compiled, got failure |
| R-042 | 🟢 | `GEN` | ✅ PASS | Bay Area Electric | compiled to services_offered |
| R-043 | 🟢 | `GEN` | ✅ PASS | Trade-named block message | compiled to services_offered |
| R-044 | 🟢 | `GEN` | ❌ FAIL | Sub-specialty | expected kind compiled, got failure |
| R-045 | 🟡 | `GEN` | ✅ PASS | DoorMaster scope | compiled to services_offered |
| R-046 | 🔴 | `GEN` | ✅ PASS | Homeowner required | compiled to customer_eligibility |
| R-047 | 🔴 | `GEN` | ✅ PASS | Roof replacement homeowner | compiled to customer_eligibility |
| R-048 | 🟡 | `GEN` | ✅ PASS | Warn-only homeowner | compiled to customer_eligibility |
| R-049 | 🟡 | `GEN` | ✅ PASS | Multi-owner authorization | compiled to customer_eligibility |
| R-050 | 🟡 | `GEN` | ✅ PASS | Existing-customer-only | compiled to customer_eligibility |
| R-051 | 🟢 | `GEN` | ⏭️ SKIP | Age requirement | SKIP-no-context: age state field absent |
| R-052 | 🟡 | `GEN` | ⏭️ SKIP | Required state fields documented | SKIP-feature-not-shipped: detail-view |
| R-053 | 🟡 | `GEN` | ✅ PASS | Eligibility no service filter | compiled to customer_eligibility |
| R-054 | 🟡 | `GEN` | ✅ PASS | Termite homeowner | compiled to customer_eligibility |
| R-055 | 🟢 | `GEN` | ✅ PASS | Eligibility with explainer | compiled to customer_eligibility |
| R-056 | 🔴 | `GEN` | ✅ PASS | 24h installs | compiled to lead_time_minimum |
| R-057 | 🔴 | `GEN` | ✅ PASS | 48h with bypass | compiled to lead_time_minimum |
| R-058 | 🟡 | `GEN` | ✅ PASS | 1-week roofing | compiled to lead_time_minimum |
| R-059 | 🟡 | `GEN` | ✅ PASS | 2-week pool | compiled to lead_time_minimum |
| R-060 | 🟡 | `GEN` | ✅ PASS | 3-week bath | compiled to lead_time_minimum |

## Section 1B NL compile (R-061..R-120)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-061 | 🔴 | `GEN` | ❌ FAIL | We're closed on Thanksgiving. | expected kind compiled, got failure |
| R-062 | 🔴 | `GEN` | ✅ PASS | We're closed Sundays. | compiled to business_hours |
| R-063 | 🔴 | `GEN` | ✅ PASS | We close at 5 PM on weekdays. | compiled to business_hours |
| R-064 | 🔴 | `GEN` | ✅ PASS | Don't take work in ZIP 33101. | compiled to service_area_zip |
| R-065 | 🔴 | `GEN` | ✅ PASS | We don't do commercial HVAC. | compiled to customer_eligibility |
| R-066 | 🔴 | `GEN` | ✅ PASS | Installations require the homeowner to authorize. | compiled to customer_eligibility |
| R-067 | 🔴 | `GEN` | ✅ PASS | We need 24 hours notice for installs. | compiled to lead_time_minimum |
| R-068 | 🔴 | `GEN` | ✅ PASS | No plumbing work on Sundays. | compiled to conditional_block |
| R-069 | 🔴 | `GEN` | ✅ PASS | We don't do roof work in rain. | compiled to conditional_block |
| R-070 | 🟡 | `GEN` | ✅ PASS | Only existing customers get same-day appointments. | compiled to conditional_block |
| R-071 | 🟡 | `GEN` | ✅ PASS | Always mention our $50 off coupon when customers ask about p | compiled to output_constraint |
| R-072 | 🟡 | `GEN` | ✅ PASS | No service after 8 PM unless it's an emergency. | compiled to conditional_block |
| R-073 | 🟡 | `GEN` | ✅ PASS | AC emergencies after hours require approval from a manager. | compiled to conditional_block |
| R-074 | 🟡 | `GEN` | ✅ PASS | Panel upgrades require a licensed electrician on the call. | compiled to conditional_block |
| R-075 | 🟡 | `GEN` | ✅ PASS | We close pool services from November to March. | compiled to conditional_block |
| R-076 | 🟡 | `GEN` | ✅ PASS | No fence installs from December to February due to frozen gr | compiled to conditional_block |
| R-077 | 🟡 | `GEN` | ❌ FAIL | Garage door repair within 24 hours guaranteed. | expected kind compiled, got failure |
| R-078 | 🟡 | `GEN` | ✅ PASS | Bathroom remodels under $5,000 we don't take. | compiled to conditional_block |
| R-079 | 🟡 | `GEN` | ⚠️ CAVEAT | No work on Sundays or after 6 PM. | compiled but rule_type business_hours != expected conditional_block |
| R-080 | 🟡 | `GEN` | ❌ FAIL | Don't take work more than 30 miles from our office. | expected kind compiled, got failure |
| R-081 | 🔴 | `GEN` | ✅ PASS | No same-day plumbing appointments after 4 PM. | compiled to conditional_block |
| R-082 | 🔴 | `GEN` | ✅ PASS | Only members of our Comfort Club get after-hours emergency s | compiled to conditional_block |
| R-083 | 🔴 | `GEN` | ✅ PASS | For homes built before 1978, AC installs need a lead-safe te | compiled to conditional_block |
| R-084 | 🔴 | `GEN` | ⚠️ CAVEAT | HOA homes need approval before we install outdoor AC units. | compiled but rule_type customer_eligibility != expected conditional_block |
| R-085 | 🔴 | `GEN` | ✅ PASS | Standard appointments need 24 hours notice but emergencies a | compiled to lead_time_minimum |
| R-086 | 🟡 | `GEN` | ✅ PASS | In Atlanta, roof replacement needs a permit pulled before we | compiled to lead_time_minimum |
| R-087 | 🟡 | `GEN` | ✅ PASS | Hydro jetting requires a camera inspection first. | compiled to conditional_block |
| R-088 | 🟡 | `GEN` | ✅ PASS | We don't service heat pumps that aren't York or Carrier. | compiled to conditional_block |
| R-089 | 🟡 | `GEN` | ❌ FAIL | No outdoor work during thunderstorms. | expected kind failure, got compiled |
| R-090 | 🟡 | `GEN` | ❌ FAIL | Customers with two unpaid invoices can't book new work. | expected kind failure, got compiled |
| R-091 | 🟡 | `GEN` | ✅ PASS | Sundays we're closed except for emergencies for members. | compiled to conditional_block |
| R-092 | 🟡 | `GEN` | ❌ FAIL | Don't book between 12 PM and 1 PM Monday through Friday — th | expected kind compiled, got failure |
| R-093 | 🟡 | `GEN` | ✅ PASS | Maintenance can be same-day but installs need 48 hours. | compiled to lead_time_minimum |
| R-094 | 🟡 | `GEN` | ✅ PASS | Pool opening service runs March to May only. | compiled to conditional_block |
| R-095 | 🟡 | `GEN` | ✅ PASS | AC installs over 5 tons need a commercial team. | compiled to conditional_block |
| R-096 | 🟡 | `GEN` | ❌ FAIL | We try not to take rush jobs unless the customer has been wi | expected kind failure, got compiled |
| R-097 | 🟡 | `GEN` | ✅ PASS | All bath remodels require an in-home consultation first. | compiled to conditional_block |
| R-098 | 🟡 | `GEN` | ❌ FAIL | Cedar fences have a 3-week material lead time but PVC is in  | expected kind compiled, got failure |
| R-099 | 🟡 | `GEN` | ❌ FAIL | Don't take work in counties where we're not licensed. | expected kind compiled, got failure |
| R-100 | 🟡 | `GEN` | ✅ PASS | We can only handle 5 installs per day. | compile-failure with 14 clarifications |
| R-101 | 🟡 | `GEN` | ❌ FAIL | After-hours emergency calls from non-members get redirected  | expected kind compiled, got failure |
| R-102 | 🟡 | `GEN` | ✅ PASS | Don't book HVAC installs on Saturdays after noon unless the  | compiled to conditional_block |
| R-103 | 🟡 | `GEN` | ✅ PASS | Emergency plumbing after 5 PM is members-only unless it's fl | compiled to conditional_block |
| R-104 | 🟡 | `GEN` | ❌ FAIL | For new customers, we require a deposit unless they're payin | expected kind failure, got compiled |
| R-105 | 🟡 | `GEN` | ✅ PASS | On Christmas Eve, only emergencies after 12 PM. | compiled to conditional_block |
| R-106 | 🟡 | `GEN` | ❌ FAIL | Real emergencies always get same-day service. | expected kind compiled, got failure |
| R-107 | 🟡 | `GEN` | ✅ PASS | Roof replacement quotes require a recent inspection or photo | compiled to customer_eligibility |
| R-108 | 🟡 | `GEN` | ✅ PASS | Pool work requires a CPO-certified tech. We don't have one i | compiled to conditional_block |
| R-109 | 🟡 | `GEN` | ✅ PASS | Panel upgrades over 200 amps need a permit and a master elec | compiled to conditional_block |
| R-110 | 🟡 | `GEN` | ❌ FAIL | After the rough-in inspection, customers can book the finish | expected kind compiled, got failure |
| R-111 | 🟡 | `GEN` | ✅ PASS | Mon-Wed are full booking; Thu-Fri only existing customers; w | compiled to conditional_block |
| R-112 | 🟡 | `GEN` | ✅ PASS | All booking rules can be overridden for life-safety emergenc | compiled to conditional_block |
| R-113 | 🟡 | `GEN` | ✅ PASS | We don't NOT take work in any ZIP we haven't explicitly excl | compile-failure with 13 clarifications |
| R-114 | 🟡 | `GEN` | ✅ PASS | Apply this rule if no other rule applies. | compile-failure with 13 clarifications |
| R-115 | 🟡 | `GEN` | ✅ PASS | During the summer (May–Sep), HVAC emergencies get priority o | compiled to conditional_block |
| R-116 | 🟡 | `GEN` | ❌ FAIL | Try to be helpful to customers. | expected kind failure, got compiled |
| R-117 | 🟡 | `GEN` | ✅ PASS | Always book emergencies, but never book after-hours. | compile-failure with 13 clarifications |
| R-118 | 🟡 | `GEN` | ❌ FAIL | VIP customers get to skip the line. | expected kind compiled, got failure |
| R-119 | 🟡 | `GEN` | ✅ PASS | Always confirm price before booking. | compiled to output_constraint |
| R-120 | 🟡 | `GEN` | ❌ FAIL | Our policies are strict. First, no work after 6 PM unless th | expected kind compiled, got failure |

## Section 1C Editing (R-121..R-150)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-121 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-121 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-122 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-122 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-123 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-123 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-124 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-124 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-125 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-125 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-126 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-126 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-127 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-127 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-128 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-128 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-129 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-129 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-130 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-130 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-131 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-131 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-132 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-132 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-133 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-133 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-134 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-134 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-135 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-135 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-136 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-136 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-137 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-137 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-138 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-138 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-139 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-139 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-140 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-140 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-141 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-141 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-142 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-142 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-143 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-143 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-144 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-144 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-145 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-145 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-146 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-146 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-147 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-147 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-148 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-148 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-149 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-149 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |
| R-150 | 🟡 | `GEN` | ⏭️ SKIP | Edit existing rule R-150 | SKIP-feature-not-shipped: edit-existing-rule modal not implemented |

## Section 1D Combinations (R-151..R-190)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-151 | 🔴 | `GEN` | ❌ FAIL | Plumbing service Sunday at ZIP 33101. | actual=accepted; rule-match=False |
| R-152 | 🔴 | `GEN` | ❌ FAIL | Plumbing Sunday ZIP 33101. | actual=accepted |
| R-153 | 🔴 | `GEN` | ❌ FAIL | Pre-1978 home Sunday booking, HVAC install. | actual=accepted; rule-match=False |
| R-154 | 🔴 | `GEN` | ✅ PASS | Tuesday HVAC repair, ZIP 32801, homeowner, built 1965, no HO | actual=accepted |
| R-155 | 🟡 | `GEN` | ❌ FAIL | ZIP 99999, HVAC repair Tuesday 10 AM. | actual=accepted; rule-match=False |
| R-156 | 🟡 | `GEN` | ✅ PASS | Tuesday 10 AM HVAC repair, ZIP 32801. | actual=accepted |
| R-157 | 🟡 | `GEN` | ❌ FAIL | Sunday + ZIP 99999 + restaurant HVAC Tuesday 10 AM. | actual=accepted |
| R-158 | 🟡 | `GEN` | ❌ FAIL | I want a new HVAC install today. | actual=accepted |
| R-159 | 🟡 | `GEN` | ❌ FAIL | Pre-1978 install — no year given, ZIP 32801. | actual=accepted |
| R-160 | 🟡 | `GEN` | ✅ PASS | Same-day install — emergency, AC dead, 95F outside, ZIP 3280 | actual=accepted |
| R-161 | 🟡 | `GEN` | ❌ FAIL | Same-day install, ZIP 32801, homeowner — no emergency mentio | actual=accepted; rule-match=False |
| R-162 | 🟡 | `GEN` | ❌ FAIL | Same-day install, NOT an emergency. | actual=accepted; rule-match=False |
| R-163 | 🟡 | `GEN` | ❌ FAIL | After-hours non-emergency call. | actual=accepted; rule-match=False |
| R-164 | 🟡 | `GEN` | ❌ FAIL | Sunday + maintenance question about our service plans. | actual=accepted; rule-match=False |
| R-165 | 🟡 | `GEN` | ❌ FAIL | Monday 6:30 PM HVAC repair, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| R-166 | 🟡 | `GEN` | ❌ FAIL | Saturday 5 PM, member, want repair. | actual=accepted; rule-match=False |
| R-167 | 🟡 | `GEN` | ✅ PASS | What services do you offer? | actual=accepted |
| R-168 | 🟡 | `GEN` | ❌ FAIL | Check availability for Sunday 10 AM HVAC. | actual=accepted; rule-match=False |
| R-169 | 🟡 | `GEN` | ❌ FAIL | Sunday + maintenance question, mention service plans. | actual=accepted; rule-match=False |
| R-170 | 🟡 | `GEN` | ❌ FAIL | Tuesday 10 AM HVAC repair, ZIP 98101 (Seattle). | actual=accepted; rule-match=False |
| R-171 | 🟡 | `GEN` | ✅ PASS | Same-day plumbing repair, ZIP 32801. | actual=accepted |
| R-172 | 🟡 | `GEN` | ❌ FAIL | Sunday roofing repair. | actual=accepted |
| R-173 | 🟡 | `GEN` | ✅ PASS | ductless_install Tuesday 10 AM ZIP 32801 homeowner. | actual=accepted |
| R-174 | 🟡 | `GEN` | ✅ PASS | Started as a renter, then said 'actually I'm the homeowner'. | actual=accepted |
| R-175 | 🟡 | `GEN` | ✅ PASS | Renter for install initially, then homeowner. | actual=accepted |
| R-176 | 🟡 | `GEN` | ❌ FAIL | Install request without year or HOA status. | actual=accepted |
| R-177 | 🟡 | `GEN` | ❌ FAIL | Sunday + plumbing + ZIP 32801 + homeowner. | actual=accepted; rule-match=False |
| R-178 | 🟡 | `GEN` | ❌ FAIL | Sunday install ZIP 33101, renter. | actual=accepted |
| R-179 | 🟡 | `GEN` | ❌ FAIL | Same-day install, member. | actual=accepted; rule-match=False |
| R-180 | 🟡 | `GEN` | ✅ PASS | Same-day install, member, with emergency. | actual=accepted |
| R-181 | 🟡 | `GEN` | ❌ FAIL | Block message templating test — Sunday booking. | actual=accepted; rule-match=False |
| R-182 | 🟡 | `GEN` | ✅ PASS | Conditional rule trigger override test. | actual=accepted |
| R-183 | 🟡 | `GEN` | ✅ PASS | Rule applies_to_tools test — escalate request. | actual=accepted |
| R-184 | 🟡 | `GEN` | ❌ FAIL | Two same-priority rules both fire — Sunday + 33101. | actual=accepted |
| R-185 | 🟡 | `GEN` | ✅ PASS | Test rule update during convo (manual setup). | actual=accepted |
| R-186 | 🟡 | `GEN` | ✅ PASS | Test rule deletion during convo (manual setup). | actual=accepted |
| R-187 | 🟡 | `GEN` | ❌ FAIL | Pre-1978 rule precondition test, year unknown. | actual=accepted |
| R-188 | 🟡 | `GEN` | ✅ PASS | Output constraint visibility in audit. | actual=accepted |
| R-189 | 🟡 | `GEN` | ❌ FAIL | Multi-rule with three different state fields needed. | actual=accepted |
| R-190 | 🟡 | `GEN` | ✅ PASS | All-rules-pass clean booking, ZIP 32801, Tuesday 10 AM, HVAC | actual=accepted |

## Section 1E Adversarial (R-191..R-230)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-191 | 🟡 | `GEN` | ❌ FAIL | Empty prompt | compile timed out: wait_until timed out (90s): /compiled\|clarif/i.test(document.body.innerText) |
| R-192 | 🟡 | `GEN` | ❌ FAIL | Whitespace-only | compile timed out: wait_until timed out (90s): /compiled\|clarif/i.test(document.body.innerText) |
| R-193 | 🟡 | `GEN` | ✅ PASS | Single word | compile-failure with 13 clarifications |
| R-194 | 🟡 | `GEN` | ✅ PASS | Gibberish | compile-failure with 13 clarifications |
| R-195 | 🟡 | `GEN` | ✅ PASS | Direct injection | compile-failure with 14 clarifications |
| R-196 | 🟡 | `GEN` | ❌ FAIL | Roleplay injection | expected kind failure, got compiled |
| R-197 | 🟡 | `GEN` | ✅ PASS | Code injection — should compile the legit part | compiled to business_hours |
| R-198 | 🟡 | `GEN` | ✅ PASS | Contradiction | compile-failure with 13 clarifications |
| R-199 | 🟡 | `GEN` | ✅ PASS | Impossibly specific | compile-failure with 14 clarifications |
| R-200 | 🟡 | `GEN` | ✅ PASS | Targets agent itself | compile-failure with 13 clarifications |
| R-201 | 🟡 | `GEN` | ✅ PASS | Admin action, not a rule | compile-failure with 13 clarifications |
| R-202 | 🟡 | `GEN` | ❌ FAIL | Cross-business identity | expected kind compiled, got failure |
| R-203 | 🟡 | `GEN` | ❌ FAIL | PII | expected kind failure, got compiled |
| R-204 | 🟡 | `GEN` | ✅ PASS | Discriminatory | compile-failure with 13 clarifications |
| R-205 | 🟡 | `GEN` | ✅ PASS | Protected-class | compile-failure with 13 clarifications |
| R-206 | 🟡 | `GEN` | ❌ FAIL | Deceptive | expected kind failure, got compiled |
| R-207 | 🟡 | `GEN` | ❌ FAIL | Trivially true | expected kind compiled, got failure |
| R-208 | 🟡 | `GEN` | ✅ PASS | Trivially false | compiled to conditional_block |
| R-209 | 🟡 | `GEN` | ✅ PASS | Spanish | compiled to business_hours |
| R-210 | 🟡 | `GEN` | ✅ PASS | Mixed Spanish/English | compiled to business_hours |
| R-211 | 🟡 | `GEN` | ✅ PASS | 5000-char prompt | compile-failure with 13 clarifications |
| R-212 | 🟡 | `GEN` | ✅ PASS | Markdown formatting | compiled to business_hours |
| R-213 | 🟡 | `GEN` | ✅ PASS | JSON-like input | compiled to business_hours |
| R-214 | 🟡 | `GEN` | ✅ PASS | Self-referential | compiled to business_hours |
| R-215 | 🟡 | `GEN` | ✅ PASS | Vague conditional | compile-failure with 13 clarifications |
| R-216 | 🟡 | `GEN` | ✅ PASS | Implied actor | compiled to business_hours |
| R-217 | 🟡 | `GEN` | ❌ FAIL | Future date | expected kind compiled, got failure |
| R-218 | 🟡 | `GEN` | ✅ PASS | Past date — still active? | compiled to services_offered |
| R-219 | 🟡 | `GEN` | ✅ PASS | Non-trade exclusion | compiled to services_offered |
| R-220 | 🟡 | `GEN` | ✅ PASS | Question, not directive | compile-failure with 13 clarifications |
| R-221 | 🟡 | `GEN` | ✅ PASS | Hostile customer focus | compile-failure with 14 clarifications |
| R-222 | 🟡 | `GEN` | ❌ FAIL | Payment terms | expected kind compiled, got failure |
| R-223 | 🟡 | `GEN` | ✅ PASS | Output constraint via meta-rule | compiled to output_constraint |
| R-224 | 🟡 | `GEN` | ✅ PASS | Conflicting w/ existing | compiled to conditional_block |
| R-225 | 🟡 | `GEN` | ✅ PASS | Possibly duplicate of seeded | compiled to business_hours |
| R-226 | 🟡 | `GEN` | ✅ PASS | Meta-instruction | compile-failure with 11 clarifications |
| R-227 | 🟡 | `GEN` | ✅ PASS | URL reference | compile-failure with 13 clarifications |
| R-228 | 🟡 | `GEN` | ❌ FAIL | Integration | expected kind compiled, got failure |
| R-229 | 🟡 | `GEN` | ✅ PASS | Real-time data | compile-failure with 14 clarifications |
| R-230 | 🟡 | `GEN` | ✅ PASS | Circular logic | compile-failure with 13 clarifications |

## Section 1F Lifecycle (R-231..R-250)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| R-231 | 🔴 | `GEN` | ❌ FAIL | Toggle off shows in UI | GTM error: page error: An object could not be cloned. |
| R-232 | 🔴 | `GEN` | ❌ FAIL | Toggle persists across reload | GTM error: page error: An object could not be cloned. |
| R-233 | 🔴 | `GEN` | ❌ FAIL | Toggle on — re-enables | GTM error: page error: An object could not be cloned. |
| R-234 | 🟡 | `GEN` | ❌ FAIL | Toggle race condition (single click) | GTM error: page error: An object could not be cloned. |
| R-235 | 🟡 | `GEN` | ❌ FAIL | Toggle on after ad-hoc disable | GTM error: page error: An object could not be cloned. |
| R-236 | 🔴 | `GEN` | ⏭️ SKIP | Delete with confirmation | SKIP-feature-not-shipped: confirmation dialog uses native confirm() which we override; behavior matches |
| R-237 | 🔴 | `GEN` | ⏭️ SKIP | Delete proceeds | SKIP-feature-not-shipped: needs full delete UI flow |
| R-238 | 🔴 | `GEN` | ⏭️ SKIP | Deleted rule doesn't fire | SKIP-feature-not-shipped: covered by toggle-off |
| R-239 | 🟡 | `GEN` | ⏭️ SKIP | Delete preserves audit | SKIP-feature-not-shipped: covered by data-design |
| R-240 | 🟡 | `GEN` | ⏭️ SKIP | Delete reversible via reset | SKIP-feature-not-shipped: covered by reset endpoint |
| R-241 | 🟡 | `GEN` | ⏭️ SKIP | Delete a rule used by tests | SKIP-feature-not-shipped: cascade is tested in tier-1 |
| R-242 | 🟡 | `GEN` | ⏭️ SKIP | Copy rule (clone) | SKIP-feature-not-shipped: no copy UI |
| R-243 | 🟢 | `GEN` | ⏭️ SKIP | Copy modifies independently | SKIP-feature-not-shipped |
| R-244 | 🟢 | `GEN` | ⏭️ SKIP | Rule version history | SKIP-feature-not-shipped |
| R-245 | 🟢 | `GEN` | ⏭️ SKIP | Rule export/import | SKIP-feature-not-shipped |
| R-246 | 🟡 | `GEN` | ⏭️ SKIP | Bulk delete | SKIP-feature-not-shipped |
| R-247 | 🟢 | `GEN` | ⏭️ SKIP | Rule search/filter | SKIP-feature-not-shipped |
| R-248 | 🟢 | `GEN` | ⏭️ SKIP | Rule status indicator | SKIP-feature-not-shipped |
| R-249 | 🟢 | `GEN` | ⏭️ SKIP | Last-fired tracked | SKIP-feature-not-shipped |
| R-250 | 🟡 | `GEN` | ⏭️ SKIP | Reset wipes changes | SKIP-feature-not-shipped: covered by admin endpoint, no UI button |

## Section 2A Single-rule chat (C-001..C-070)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-001 | 🔴 | `GEN` | ✅ PASS | I'd like to book HVAC service Tuesday at 10 AM, ZIP 32801. | actual=accepted |
| C-002 | 🔴 | `GEN` | ❌ FAIL | Can someone come Sunday at 10 AM? My AC is broken. | actual=accepted; rule-match=False |
| C-003 | 🔴 | `GEN` | ❌ FAIL | Can you come tonight at 9 PM? | actual=accepted; rule-match=False |
| C-004 | 🔴 | `GEN` | ❌ FAIL | Can you come at 6 AM tomorrow before I leave for work? | actual=accepted; rule-match=False |
| C-005 | 🔴 | `GEN` | ✅ PASS | Book me Saturday at 9 AM, ZIP 32801. | actual=accepted |
| C-006 | 🔴 | `GEN` | ❌ FAIL | Saturday at 5 PM please. | actual=accepted; rule-match=False |
| C-007 | 🟡 | `GEN` | ❌ FAIL | Can someone come this Sunday? | actual=accepted; rule-match=False |
| C-008 | 🟡 | `GEN` | ✅ PASS | Need someone to come after work. | actual=accepted |
| C-009 | 🟡 | `GEN` | ✅ PASS | Book me for July 4th at noon. | actual=accepted |
| C-010 | 🟡 | `GEN` | ❌ FAIL | I'm in California — can I book for 10 PM CA time on Friday? | actual=accepted; rule-match=False |
| C-011 | 🔴 | `GEN` | ✅ PASS | My ZIP is 32801, need HVAC service Wednesday at 9 AM. | actual=accepted |
| C-012 | 🔴 | `GEN` | ❌ FAIL | ZIP 90210, need plumbing. | actual=accepted; rule-match=False |
| C-013 | 🔴 | `GEN` | ❌ FAIL | 33101, AC broken Wednesday. | actual=accepted; rule-match=False |
| C-014 | 🔴 | `GEN` | ❌ FAIL | 32202, need a plumber. | actual=accepted; rule-match=False |
| C-015 | 🟡 | `GEN` | ✅ PASS | 32746, HVAC tune-up Wednesday 10 AM. | actual=accepted |
| C-016 | 🟡 | `GEN` | ❌ FAIL | I'm in Orlando, can you come out? | actual=accepted |
| C-017 | 🟡 | `GEN` | ❌ FAIL | Near Orlando, by the lake. | actual=accepted |
| C-018 | 🟡 | `GEN` | ✅ PASS | 32801-1234, need service Wednesday 10 AM. | actual=accepted |
| C-019 | 🟡 | `GEN` | ✅ PASS | ZIP is 123. | actual=accepted |
| C-020 | 🟡 | `GEN` | ❌ FAIL | I'm in Sanford. | actual=accepted |
| C-021 | 🔴 | `GEN` | ✅ PASS | My AC isn't cooling, can you look at it Wednesday at 10 AM,  | actual=accepted |
| C-022 | 🔴 | `GEN` | ✅ PASS | Need AC service for our restaurant. | actual=accepted |
| C-023 | 🔴 | `GEN` | ❌ FAIL | Can you fix my roof? | actual=accepted; rule-match=False |
| C-024 | 🔴 | `GEN` | ✅ PASS | I have a leaky faucet, can you come Wednesday 10 AM ZIP 3280 | actual=accepted |
| C-025 | 🔴 | `GEN` | ✅ PASS | Need an outlet replaced in my kitchen Wednesday 10 AM, ZIP 3 | actual=accepted |
| C-026 | 🟡 | `GEN` | ✅ PASS | My dishwasher is broken. | actual=accepted |
| C-027 | 🟡 | `GEN` | ✅ PASS | Interested in solar panels. | actual=accepted |
| C-028 | 🟡 | `GEN` | ✅ PASS | Want an EV charger installed Wednesday 10 AM, ZIP 32801, hom | actual=accepted |
| C-029 | 🟡 | `GEN` | ✅ PASS | Whole-house generator install Wednesday, ZIP 32801, homeowne | actual=accepted |
| C-030 | 🟡 | `GEN` | ❌ FAIL | My pool pump is broken. | actual=accepted; rule-match=False |
| C-031 | 🔴 | `GEN` | ✅ PASS | I own my home, want a new HVAC install next Friday at 9 AM,  | actual=accepted |
| C-032 | 🔴 | `GEN` | ✅ PASS | I'm renting an apartment and want to install AC. | actual=accepted |
| C-033 | 🔴 | `GEN` | ✅ PASS | I'm renting and my AC needs repair Wednesday 10 AM, ZIP 3280 | actual=accepted |
| C-034 | 🟡 | `GEN` | ✅ PASS | I manage this property; the owner said it's fine to install. | actual=accepted |
| C-035 | 🟡 | `GEN` | ✅ PASS | My partner and I co-own; can I authorize? | actual=accepted |
| C-036 | 🟡 | `GEN` | ✅ PASS | My mom owns the house, can I book service for her? | actual=accepted |
| C-037 | 🟡 | `GEN` | ✅ PASS | Yeah I own it, ZIP 32801, HVAC tune-up Wednesday 10 AM. | actual=accepted |
| C-038 | 🟡 | `GEN` | ❌ FAIL | The house I live in. | actual=accepted |
| C-039 | 🟡 | `GEN` | ✅ PASS | I own the duplex but the tenant is in the unit needing servi | actual=accepted |
| C-040 | 🟡 | `GEN` | ✅ PASS | Started as a renter, then homeowner. | actual=accepted |
| C-041 | 🔴 | `GEN` | ✅ PASS | New HVAC install next Friday please. I own and I'm in 32801. | actual=accepted |
| C-042 | 🔴 | `GEN` | ❌ FAIL | I need a new AC today, my old one died, ZIP 32801, homeowner | actual=accepted; rule-match=False |
| C-043 | 🔴 | `GEN` | ❌ FAIL | Install tomorrow at noon, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-044 | 🔴 | `GEN` | ✅ PASS | Install Thursday at 9 AM, ZIP 32801, homeowner. | actual=accepted |
| C-045 | 🟡 | `GEN` | ✅ PASS | My AC needs repair today, ZIP 32801. | actual=accepted |
| C-046 | 🟡 | `GEN` | ✅ PASS | AC died and it's 95° in the house. ZIP 32801, homeowner. | actual=accepted |
| C-047 | 🟡 | `GEN` | ✅ PASS | Emergency! Install AC today, ZIP 32801, homeowner! | actual=accepted |
| C-048 | 🟡 | `GEN` | ✅ PASS | Install in exactly 48 hours, ZIP 32801, homeowner. | actual=accepted |
| C-049 | 🟡 | `GEN` | ❌ FAIL | Install in 47 hours, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-050 | 🟡 | `GEN` | ✅ PASS | Soonest you can install AC? | actual=accepted |
| C-051 | 🔴 | `GEN` | ✅ PASS | My AC just died, it's 10 PM, can someone come? | actual=accepted |
| C-052 | 🔴 | `GEN` | ✅ PASS | AC died, it's 10 PM, I'm a Care Club member. | actual=accepted |
| C-053 | 🔴 | `GEN` | ✅ PASS | AC died, it's noon. | actual=accepted |
| C-054 | 🔴 | `GEN` | ✅ PASS | Just calling at 10 PM to schedule a tune-up next week. | actual=accepted |
| C-055 | 🟡 | `GEN` | ❌ FAIL | Sunday noon, my AC died. | actual=accepted |
| C-056 | 🟡 | `GEN` | ✅ PASS | It's 6:59 PM Monday, AC died. | actual=accepted |
| C-057 | 🟡 | `GEN` | ✅ PASS | It's 7:00 PM exactly, AC died. | actual=accepted |
| C-058 | 🟡 | `GEN` | ✅ PASS | It's 9 PM, AC isn't cooling that well, getting warm. | actual=accepted |
| C-059 | 🟡 | `GEN` | ✅ PASS | It's 10 PM, no AC at all in a heat wave. | actual=accepted |
| C-060 | 🟡 | `GEN` | ✅ PASS | Hey it's Joe from last spring, AC died, 10 PM. | actual=accepted |
| C-061 | 🔴 | `GEN` | ✅ PASS | Drain cleaning today at 2 PM ZIP 32801. | actual=accepted |
| C-062 | 🔴 | `GEN` | ✅ PASS | Slow drain at 4:30 PM, want to fix today, been bad all week, | actual=accepted |
| C-063 | 🔴 | `GEN` | ✅ PASS | Burst pipe in the kitchen 4:30 PM, water everywhere, ZIP 328 | actual=accepted |
| C-064 | 🟡 | `GEN` | ✅ PASS | Schedule a plumber for tomorrow 9 AM, ZIP 32801. | actual=accepted |
| C-065 | 🟡 | `GEN` | ✅ PASS | AC needs same-day repair at 4:30 PM, ZIP 32801. | actual=accepted |
| C-066 | 🟡 | `GEN` | ✅ PASS | Same-day drain cleaning at 4:00 PM, ZIP 32801. | actual=accepted |
| C-067 | 🟡 | `GEN` | ✅ PASS | Toilet won't flush at 5 PM, only bathroom in the house, ZIP  | actual=accepted |
| C-068 | 🟡 | `GEN` | ✅ PASS | Sewage backing up in basement at 6 PM, ZIP 32801. | actual=accepted |
| C-069 | 🟡 | `GEN` | ✅ PASS | Pipe flooding 4:45 PM, ZIP 32801. | actual=accepted |
| C-070 | 🟡 | `GEN` | ✅ PASS | Drain cleaning today, kind of urgent, ZIP 32801. | actual=accepted |

## Section 2B Boundaries (C-071..C-120)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-071 | 🔴 | `GEN` | ✅ PASS | Saturday 8 AM appointment, HVAC repair, ZIP 32801. | actual=accepted |
| C-072 | 🔴 | `GEN` | ❌ FAIL | Saturday 7:59 AM HVAC repair, ZIP 32801. | actual=accepted; rule-match=False |
| C-073 | 🔴 | `GEN` | ✅ PASS | Saturday 4:00 PM HVAC repair, ZIP 32801. | actual=accepted |
| C-074 | 🔴 | `GEN` | ✅ PASS | Saturday 3:59 PM HVAC repair, ZIP 32801. | actual=accepted |
| C-075 | 🔴 | `GEN` | ❌ FAIL | Saturday 4:01 PM HVAC repair, ZIP 32801. | actual=accepted; rule-match=False |
| C-076 | 🔴 | `GEN` | ✅ PASS | Monday 7 AM HVAC repair, ZIP 32801. | actual=accepted |
| C-077 | 🔴 | `GEN` | ❌ FAIL | Monday 6:59 AM HVAC repair, ZIP 32801. | actual=accepted; rule-match=False |
| C-078 | 🟡 | `GEN` | ❌ FAIL | Friday 7:01 PM HVAC repair, ZIP 32801. | actual=accepted; rule-match=False |
| C-079 | 🟡 | `GEN` | ❌ FAIL | Schedule 2:30 AM second Sunday March (DST-spring), HVAC, ZIP | actual=accepted; rule-match=False |
| C-080 | 🟡 | `GEN` | ❌ FAIL | 1:30 AM second Sunday November (DST-fall), HVAC, ZIP 32801. | actual=accepted; rule-match=False |
| C-081 | 🟡 | `GEN` | ❌ FAIL | Book me Saturday at 8. | actual=accepted |
| C-082 | 🟡 | `GEN` | ✅ PASS | Saturday 15:00 HVAC, ZIP 32801. | actual=accepted |
| C-083 | 🔴 | `GEN` | ✅ PASS | 32801 (first allowed ZIP) HVAC repair Mon 9 AM. | actual=accepted |
| C-084 | 🔴 | `GEN` | ✅ PASS | 32839 (last allowed ZIP) HVAC repair Mon 9 AM. | actual=accepted |
| C-085 | 🔴 | `GEN` | ❌ FAIL | 32840 ZIP HVAC repair Mon 9 AM. | actual=accepted; rule-match=False |
| C-086 | 🔴 | `GEN` | ❌ FAIL | 32800 ZIP HVAC repair Mon 9 AM. | actual=accepted; rule-match=False |
| C-087 | 🟡 | `GEN` | ❌ FAIL | 01234 ZIP HVAC repair Mon 9 AM. | actual=accepted; rule-match=False |
| C-088 | 🟡 | `GEN` | ✅ PASS | 32839-9999 HVAC repair Mon 9 AM. | actual=accepted |
| C-089 | 🟡 | `GEN` | ✅ PASS | 32839-12 HVAC repair Mon 9 AM. | actual=accepted |
| C-090 | 🟡 | `GEN` | ✅ PASS | Orlandoo 32801 HVAC repair Mon 9 AM. | actual=accepted |
| C-091 | 🟡 | `GEN` | ❌ FAIL | I'm in Florida. | actual=accepted |
| C-092 | 🟡 | `GEN` | ❌ FAIL | 34759 HVAC repair Mon 9 AM. | actual=accepted; rule-match=False |
| C-093 | 🔴 | `GEN` | ✅ PASS | Install in exactly 48 hours, ZIP 32801, homeowner. | actual=accepted |
| C-094 | 🔴 | `GEN` | ❌ FAIL | Install in 47 hours 59 minutes, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-095 | 🔴 | `GEN` | ✅ PASS | Install in 48 hours 1 minute, ZIP 32801, homeowner. | actual=accepted |
| C-096 | 🟡 | `GEN` | ✅ PASS | Earliest possible install, ZIP 32801, homeowner. | actual=accepted |
| C-097 | 🟡 | `GEN` | ❌ FAIL | Install tomorrow same time, AC, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-098 | 🟡 | `GEN` | ✅ PASS | Install in a month, ZIP 32801, homeowner. | actual=accepted |
| C-099 | 🟡 | `GEN` | ✅ PASS | Move my Thursday install to tomorrow, ZIP 32801. | actual=accepted |
| C-100 | 🟡 | `GEN` | ✅ PASS | Emergency, AC died, ASAP install, ZIP 32801, homeowner. | actual=accepted |
| C-101 | 🟡 | `GEN` | ❌ FAIL | Install today at 2 PM during business hours, ZIP 32801, home | actual=accepted; rule-match=False |
| C-102 | 🟡 | `GEN` | ❌ FAIL | Install today, member, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-103 | 🔴 | `GEN` | ✅ PASS | AC install, house built 1977, ZIP 32801, homeowner. | actual=accepted |
| C-104 | 🔴 | `GEN` | ✅ PASS | AC install, house built 1978, ZIP 32801, homeowner. | actual=accepted |
| C-105 | 🟡 | `GEN` | ✅ PASS | AC install, house built 1850, ZIP 32801, homeowner. | actual=accepted |
| C-106 | 🟡 | `GEN` | ✅ PASS | AC install, house built 2050, ZIP 32801, homeowner. | actual=accepted |
| C-107 | 🟡 | `GEN` | ❌ FAIL | AC install, year unknown, ZIP 32801, homeowner. | actual=accepted |
| C-108 | 🟡 | `GEN` | ❌ FAIL | AC install, built sometime in the 70s, ZIP 32801, homeowner. | actual=accepted |
| C-109 | 🔴 | `GEN` | ✅ PASS | HOA, want outdoor AC condenser installed, ZIP 32801, homeown | actual=accepted |
| C-110 | 🔴 | `GEN` | ✅ PASS | HOA, interior unit replacement, ZIP 32801, homeowner. | actual=accepted |
| C-111 | 🔴 | `GEN` | ✅ PASS | No HOA, outdoor condenser install, ZIP 32801, homeowner. | actual=accepted |
| C-112 | 🟡 | `GEN` | ❌ FAIL | Outdoor AC install, HOA status unknown, ZIP 32801, homeowner | actual=accepted |
| C-113 | 🟡 | `GEN` | ✅ PASS | HOA, customer claims pre-approval verbal, install, ZIP 32801 | actual=accepted |
| C-114 | 🟡 | `GEN` | ✅ PASS | Condo with HOA, new outdoor unit, ZIP 32801, homeowner. | actual=accepted |
| C-115 | 🟡 | `GEN` | ✅ PASS | I was a Care Club member last year, can I get after-hours se | actual=accepted |
| C-116 | 🟡 | `GEN` | ✅ PASS | My friend's a member, can he transfer benefits? | actual=accepted |
| C-117 | 🟡 | `GEN` | ✅ PASS | Sign me up for Care Club right now then send someone. | actual=accepted |
| C-118 | 🟡 | `GEN` | ✅ PASS | I'm a Premier member. | actual=accepted |
| C-119 | 🟡 | `GEN` | ✅ PASS | Member during hours wants to reserve 11 PM tonight. | actual=accepted |
| C-120 | 🟡 | `GEN` | ✅ PASS | Member calling at 9 PM to schedule tune-up. | actual=accepted |

## Section 2C State gathering (C-121..C-160)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-121 | 🔴 | `GEN` | ❌ FAIL | I want a new HVAC install. | actual=accepted |
| C-122 | 🔴 | `GEN` | ✅ PASS | Need an HVAC install Friday at 10 AM. | actual=accepted |
| C-123 | 🟡 | `GEN` | ✅ PASS | I'm at 3, 2, 8, 0, 1, HVAC repair Wednesday 10 AM, homeowner | actual=accepted |
| C-124 | 🟡 | `GEN` | ✅ PASS | 123 Main St Orlando FL 32801, HVAC repair Wednesday 10 AM, h | actual=accepted |
| C-125 | 🟡 | `GEN` | ✅ PASS | 32801 HVAC repair Wednesday 10 AM, homeowner. | actual=accepted |
| C-126 | 🟡 | `GEN` | ✅ PASS | I have two properties — 32801 and 32839. | actual=accepted |
| C-127 | 🔴 | `GEN` | ✅ PASS | I want to upgrade my house's AC, Wednesday 10 AM, ZIP 32801. | actual=accepted |
| C-128 | 🔴 | `GEN` | ✅ PASS | I own the home, HVAC install Friday 10 AM, ZIP 32801. | actual=accepted |
| C-129 | 🔴 | `GEN` | ✅ PASS | I'm renting, want HVAC install Friday 10 AM, ZIP 32801. | actual=accepted |
| C-130 | 🟡 | `GEN` | ✅ PASS | I'm renting, want install. | actual=accepted |
| C-131 | 🟡 | `GEN` | ✅ PASS | It's my parents' house but I take care of everything. | actual=accepted |
| C-132 | 🟡 | `GEN` | ✅ PASS | Why do you need to know if I own? | actual=accepted |
| C-133 | 🔴 | `GEN` | ✅ PASS | AC died, 95° in the house, my elderly mom is here, ZIP 32801 | actual=accepted |
| C-134 | 🔴 | `GEN` | ✅ PASS | It's an emergency, AC died, ZIP 32801, homeowner. | actual=accepted |
| C-135 | 🟡 | `GEN` | ✅ PASS | Emergency! Install AC today! | actual=accepted |
| C-136 | 🟡 | `GEN` | ✅ PASS | AC's been off three days but it's not really an emergency, Z | actual=accepted |
| C-137 | 🟡 | `GEN` | ✅ PASS | Slow leak. | actual=accepted |
| C-138 | 🟡 | `GEN` | ✅ PASS | Slow drain that's progressive AND my water heater just burst | actual=accepted |
| C-139 | 🔴 | `GEN` | ✅ PASS | House built 1962, AC install, ZIP 32801, homeowner. | actual=accepted |
| C-140 | 🟡 | `GEN` | ✅ PASS | Built in the 60s, AC install, ZIP 32801, homeowner. | actual=accepted |
| C-141 | 🟡 | `GEN` | ❌ FAIL | No idea when it was built, AC install, ZIP 32801, homeowner. | actual=accepted |
| C-142 | 🟡 | `GEN` | ✅ PASS | House is about 80 years old, AC install, ZIP 32801, homeowne | actual=accepted |
| C-143 | 🟡 | `GEN` | ✅ PASS | Built 19852, AC install, ZIP 32801, homeowner. | actual=accepted |
| C-144 | 🔴 | `GEN` | ✅ PASS | I'm in The Springs HOA, AC install, ZIP 32801, homeowner. | actual=accepted |
| C-145 | 🟡 | `GEN` | ❌ FAIL | Not sure if there's an HOA, AC install, ZIP 32801, homeowner | actual=accepted |
| C-146 | 🟡 | `GEN` | ✅ PASS | No HOA, just my house. AC install, ZIP 32801, homeowner. | actual=accepted |
| C-147 | 🟡 | `GEN` | ❌ FAIL | Want a new AC install. | actual=accepted |
| C-148 | 🟡 | `GEN` | ✅ PASS | 32801, I own it, built 1972, no HOA, AC install Friday 10 AM | actual=accepted |
| C-149 | 🟡 | `GEN` | ✅ PASS | Built 1972, no HOA, 32801, own it, AC install Friday 10 AM. | actual=accepted |
| C-150 | 🟡 | `GEN` | ❌ FAIL | What's the ZIP, ownership, year, HOA? | actual=accepted |
| C-151 | 🟡 | `GEN` | ✅ PASS | What year was your home built? | actual=accepted |
| C-152 | 🟡 | `GEN` | ✅ PASS | AC install Friday 10 AM, ZIP 32801, I own. | actual=accepted |
| C-153 | 🟡 | `GEN` | ✅ PASS | Want HVAC install. | actual=accepted |
| C-154 | 🟡 | `GEN` | ❌ FAIL | AC install, ZIP 32801. | actual=accepted |
| C-155 | 🟡 | `GEN` | ❌ FAIL | AC install, year unknown. | actual=accepted |
| C-156 | 🟡 | `GEN` | ✅ PASS | My HOA already approved it, AC install ZIP 32801 homeowner F | actual=accepted |
| C-157 | 🟡 | `GEN` | ✅ PASS | 100 Main St, Lake Mary FL 32746, HVAC repair Wednesday 10 AM | actual=accepted |
| C-158 | 🟡 | `GEN` | ❌ FAIL | My number is 407-555-1234, HVAC repair Wednesday 10 AM. | actual=accepted |
| C-159 | 🟡 | `GEN` | ❌ FAIL | My email is foo@bar.com, HVAC repair Wednesday 10 AM. | actual=accepted |
| C-160 | 🟡 | `GEN` | ✅ PASS | 32801, homeowner, want HVAC install Friday 10 AM. | actual=accepted |

## Section 2D Multi-rule (C-161..C-200)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-161 | 🔴 | `GEN` | ❌ FAIL | Plumbing service Sunday at 10 AM ZIP 33101. | actual=accepted |
| C-162 | 🔴 | `GEN` | ❌ FAIL | Sunday service for our restaurant. | actual=accepted |
| C-163 | 🔴 | `GEN` | ❌ FAIL | Restaurant in Miami needs HVAC service. | actual=accepted |
| C-164 | 🔴 | `GEN` | ❌ FAIL | I'm renting at 33101 and want a new AC. | actual=accepted; rule-match=False |
| C-165 | 🔴 | `GEN` | ❌ FAIL | Install AC Sunday morning, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-166 | 🟡 | `GEN` | ❌ FAIL | Install AC immediately at 10 PM, ZIP 32801, homeowner. | actual=accepted; rule-match=False |
| C-167 | 🟡 | `GEN` | ❌ FAIL | Schedule install for tomorrow morning at 10 PM, ZIP 32801, h | actual=accepted; rule-match=False |
| C-168 | 🟡 | `GEN` | ❌ FAIL | Sunday at 11 AM burst pipe, ZIP 32801, not a member. | actual=accepted; rule-match=False |
| C-169 | 🟡 | `GEN` | ✅ PASS | Outdoor AC install, HOA, house built 1965, ZIP 32801, homeow | actual=accepted |
| C-170 | 🟡 | `GEN` | ❌ FAIL | Renter install, house built 1960, ZIP 32801. | actual=accepted |
| C-171 | 🟡 | `GEN` | ❌ FAIL | Slow drain at 4:30 PM, today please, in HOA, ZIP 32801. | actual=accepted |
| C-172 | 🟡 | `GEN` | ❌ FAIL | Sunday install ZIP 33101 renter. | actual=accepted |
| C-173 | 🟡 | `GEN` | ❌ FAIL | Sunday 10 PM AC install ZIP 33101 renter no AC dying. | actual=accepted |
| C-174 | 🟡 | `GEN` | ❌ FAIL | Kitchen-sink request hitting all 10 rules: Sunday 10 PM AC i | actual=accepted |
| C-175 | 🟡 | `GEN` | ✅ PASS | Tuesday 10 AM, HVAC repair, ZIP 32801, homeowner, built 2000 | actual=accepted |
| C-176 | 🟡 | `GEN` | ✅ PASS | After-hours emergency, non-member, plumbing flooding, ZIP 32 | actual=accepted |
| C-177 | 🟡 | `GEN` | ❌ FAIL | Same priority rules: Sunday + out-of-area. | actual=accepted |
| C-178 | 🟡 | `GEN` | ✅ PASS | Disabled rule_06 then send after-hours emergency. | actual=accepted |
| C-179 | 🟡 | `GEN` | ❌ FAIL | Renter install pre-1978, ZIP 32801. | actual=accepted |
| C-180 | 🟡 | `GEN` | ✅ PASS | Two warns scenario. | actual=accepted |
| C-181 | 🟡 | `GEN` | ❌ FAIL | Output constraint plus Sunday block: Sunday tune-up question | actual=accepted; rule-match=False |
| C-182 | 🟡 | `GEN` | ✅ PASS | Emergency same-day install with is_emergency=True, ZIP 32801 | actual=accepted |
| C-183 | 🟡 | `GEN` | ❌ FAIL | Emergency same-day install but renter, ZIP 32801. | actual=accepted |
| C-184 | 🟡 | `GEN` | ✅ PASS | Tuesday 10 AM HVAC repair ZIP 32801 homeowner — clean bookin | actual=accepted |
| C-185 | 🟡 | `GEN` | ✅ PASS | Custom-priority rule fires first. | actual=accepted |
| C-186 | 🟡 | `GEN` | ✅ PASS | Renter install then says homeowner. | actual=accepted |
| C-187 | 🟡 | `GEN` | ❌ FAIL | Renter install on Sunday then says homeowner. | actual=accepted; rule-match=False |
| C-188 | 🟡 | `GEN` | ✅ PASS | Customer chains around rules: Sunday → Monday. | actual=accepted |
| C-189 | 🟡 | `GEN` | ❌ FAIL | Customer cycles between two impossible options. | actual=accepted; rule-match=False |
| C-190 | 🟡 | `GEN` | ✅ PASS | State gathered for one purpose, repurposed. | actual=accepted |
| C-191 | 🟡 | `GEN` | ✅ PASS | Update my address to 32802, then booking. | actual=accepted |
| C-192 | 🟡 | `GEN` | ✅ PASS | HVAC install then plumbing repair, two services. | actual=accepted |
| C-193 | 🟡 | `GEN` | ✅ PASS | Check availability for Tuesday 10 AM, then book. | actual=accepted |
| C-194 | 🟡 | `GEN` | ❌ FAIL | Lookup service area for 33101, then book. | actual=accepted; rule-match=False |
| C-195 | 🟡 | `GEN` | ✅ PASS | Tool-specific rule scenario. | actual=accepted |
| C-196 | 🟡 | `GEN` | ❌ FAIL | Sunday booking attempted twice in same conversation. | actual=accepted; rule-match=False |
| C-197 | 🟡 | `GEN` | ✅ PASS | Customer asks: what rules am I hitting? | actual=accepted |
| C-198 | 🟡 | `GEN` | ✅ PASS | Customer references previous block. | actual=accepted |
| C-199 | 🟡 | `GEN` | ✅ PASS | Output constraint adapts to multi-rule context. | actual=accepted |
| C-200 | 🟡 | `GEN` | ✅ PASS | Long convo with cohesion. | actual=accepted |

## Section 2E LLM judge calibration (C-201..C-230)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-201 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Pipe burst, water everywhere | 0/1 blocked (judge-non-emergency interpretation) |
| C-202 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Basement is flooding | 0/1 blocked (judge-non-emergency interpretation) |
| C-203 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Sewage backing up into the bathtub | 0/1 blocked (judge-non-emergency interpretation) |
| C-204 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | No water in the house at all | 0/1 blocked (judge-non-emergency interpretation) |
| C-205 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Water heater leaking and floor is wet | 0/1 blocked (judge-non-emergency interpretation) |
| C-206 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | AC dead, 95° outside | 0/1 blocked (judge-non-emergency interpretation) |
| C-207 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Smoke from outdoor AC unit | 0/1 blocked (judge-non-emergency interpretation) |
| C-208 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | I smell gas in the house | 0/1 blocked (judge-non-emergency interpretation) |
| C-209 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Sparks from outlet | 0/1 blocked (judge-non-emergency interpretation) |
| C-210 | 🔴 | `GEN` `JUDGE` | ❌ FAIL | Pipe burst, freezing weather | 0/1 blocked (judge-non-emergency interpretation) |
| C-211 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Slow drain getting worse over a few weeks | 0/1 blocked (judge-non-emergency interpretation) |
| C-212 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Schedule a plumber for next Tuesday | 0/1 blocked (judge-non-emergency interpretation) |
| C-213 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Just want to schedule a routine tune-up | 0/1 blocked (judge-non-emergency interpretation) |
| C-214 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | My filter is dirty, need a fresh one | 0/1 blocked (judge-non-emergency interpretation) |
| C-215 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | What services do you offer? | 0/1 blocked (judge-non-emergency interpretation) |
| C-216 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Bathroom faucet has a little drip | 0/1 blocked (judge-non-emergency interpretation) |
| C-217 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | AC works fine but I want it cleaned | 0/1 blocked (judge-non-emergency interpretation) |
| C-218 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | One outlet in the guest room isn't working | 0/1 blocked (judge-non-emergency interpretation) |
| C-219 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Estimate for a new AC sometime | 0/1 blocked (judge-non-emergency interpretation) |
| C-220 | 🔴 | `GEN` `JUDGE` | ⚠️ CAVEAT | Pre-season tune-up | 0/1 blocked (judge-non-emergency interpretation) |
| C-221 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Toilet won't flush | 0/3 blocked (judge-non-emergency interpretation) |
| C-222 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | AC isn't cooling super well lately | 0/3 blocked (judge-non-emergency interpretation) |
| C-223 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Water heater isn't producing hot water | 0/3 blocked (judge-non-emergency interpretation) |
| C-224 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Heater stopped working, it's 40° outside | 0/3 blocked (judge-non-emergency interpretation) |
| C-225 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Drain cleaning today, kind of urgent | 1/3 blocked (judge-non-emergency interpretation) |
| C-226 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Need plumber ASAP for clogged sink | 1/3 blocked (judge-non-emergency interpretation) |
| C-227 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | AC vents are weak | 1/3 blocked (judge-non-emergency interpretation) |
| C-228 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Slow leak under sink, not bad yet | 0/3 blocked (judge-non-emergency interpretation) |
| C-229 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Active leak under sink | 0/3 blocked (judge-non-emergency interpretation) |
| C-230 | 🟡 | `GEN` `JUDGE` | ⚠️ CAVEAT | Just an emergency really, please come | 0/3 blocked (judge-non-emergency interpretation) |

## Section 2F Output constraint (C-231..C-250)

| ID | Sev | Tags | Status | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-231 | 🔴 | `GEN` `OUTPUT` | ⚠️ CAVEAT | How often should I have my HVAC maintained? | actual=accepted; required-substring='comfort club'=False |
| C-232 | 🔴 | `GEN` `OUTPUT` | ⚠️ CAVEAT | How much for an HVAC tune-up? | actual=accepted; required-substring='comfort club'=False |
| C-233 | 🔴 | `GEN` `OUTPUT` | ⚠️ CAVEAT | AC and plumbing both have issues, can I bundle? | actual=accepted; required-substring='comfort club'=False |
| C-234 | 🔴 | `GEN` `OUTPUT` | ✅ PASS | Do you offer service plans? | actual=accepted; required-substring='comfort club'=True |
| C-235 | 🔴 | `GEN` `OUTPUT` | ⚠️ CAVEAT | I need a panel upgrade, ballpark price? | actual=accepted; required-substring='comfort club'=False |
| C-236 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | What if my AC dies on a weekend? | actual=accepted; required-substring='comfort club'=True |
| C-237 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | I've been with you for years, any benefits? | actual=accepted; required-substring='comfort club'=True |
| C-238 | 🟡 | `GEN` `OUTPUT` | ⚠️ CAVEAT | Do you offer any discounts? | actual=accepted; required-substring='comfort club'=False |
| C-239 | 🔴 | `GEN` `OUTPUT` | ✅ PASS | What time is my appointment tomorrow? | actual=accepted; forbidden-substring-present=False |
| C-240 | 🔴 | `GEN` `OUTPUT` | ✅ PASS | Do you stock 5-ton AC units? | actual=accepted; forbidden-substring-present=False |
| C-241 | 🔴 | `GEN` `OUTPUT` | ✅ PASS | What size truck will the tech bring? | actual=accepted; forbidden-substring-present=False |
| C-242 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | Just answer my question, don't pitch me. Do you do HVAC repa | actual=accepted; forbidden-substring-present=False |
| C-243 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | AC died, my elderly mom is here, can someone come? | actual=accepted; forbidden-substring-present=False |
| C-244 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | Earlier I declined Care Club. Now another maintenance questi | actual=accepted; forbidden-substring-present=False |
| C-245 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | Member: how much for a tune-up? | actual=accepted |
| C-246 | 🟡 | `GEN` `OUTPUT` | ⚠️ CAVEAT | Tell me about Care Club. | actual=accepted; required-substring='comfort club'=False |
| C-247 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | Just got laid off, need to budget service costs. | actual=accepted |
| C-248 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | 33101, what services? | actual=accepted; forbidden-substring-present=False |
| C-249 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | I want to cancel my appointment. | actual=accepted; forbidden-substring-present=False |
| C-250 | 🟡 | `GEN` `OUTPUT` | ✅ PASS | What's your cancellation policy? | actual=accepted; forbidden-substring-present=False |

## Gap inventory (skip reasons)

| Reason | Count | Test IDs (first 8) |
| --- | --- | --- |
| SKIP-feature-not-shipped: edit-existing-rule modal not implemented | 30 | R-121, R-122, R-123, R-124, R-125, R-126, R-127, R-128 … |
| SKIP-feature-not-shipped | 7 | R-243, R-244, R-245, R-246, R-247, R-248, R-249 |
| SKIP-feature-not-shipped: structured form validation | 3 | R-006, R-011, R-013 |
| SKIP-feature-not-shipped: split-shift form | 2 | R-002, R-008 |
| SKIP-feature-not-shipped: edit modal | 2 | R-029, R-030 |
| SKIP-feature-not-shipped: timezone autocomplete | 1 | R-007 |
| SKIP-feature-not-shipped: structured form | 1 | R-009 |
| SKIP-no-context: age state field absent | 1 | R-051 |
| SKIP-feature-not-shipped: detail-view | 1 | R-052 |
| SKIP-feature-not-shipped: confirmation dialog uses native confirm() which we override; behavior matches | 1 | R-236 |
| SKIP-feature-not-shipped: needs full delete UI flow | 1 | R-237 |
| SKIP-feature-not-shipped: covered by toggle-off | 1 | R-238 |
| SKIP-feature-not-shipped: covered by data-design | 1 | R-239 |
| SKIP-feature-not-shipped: covered by reset endpoint | 1 | R-240 |
| SKIP-feature-not-shipped: cascade is tested in tier-1 | 1 | R-241 |
| SKIP-feature-not-shipped: no copy UI | 1 | R-242 |
| SKIP-feature-not-shipped: covered by admin endpoint, no UI button | 1 | R-250 |

## LLM-judge calibration (Section 2E)

| ID | Severity | Customer message (gist) | Expected | Samples blocked | Evidence |
| --- | --- | --- | --- | --- | --- |
| C-201 | 🔴 | Pipe burst, water everywhere | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-202 | 🔴 | Basement is flooding | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-203 | 🔴 | Sewage backing up into the bathtub | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-204 | 🔴 | No water in the house at all | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-205 | 🔴 | Water heater leaking and floor is wet | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-206 | 🔴 | AC dead, 95° outside | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-207 | 🔴 | Smoke from outdoor AC unit | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-208 | 🔴 | I smell gas in the house | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-209 | 🔴 | Sparks from outlet | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-210 | 🔴 | Pipe burst, freezing weather | true | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-211 | 🔴 | Slow drain getting worse over a few weeks | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-212 | 🔴 | Schedule a plumber for next Tuesday | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-213 | 🔴 | Just want to schedule a routine tune-up | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-214 | 🔴 | My filter is dirty, need a fresh one | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-215 | 🔴 | What services do you offer? | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-216 | 🔴 | Bathroom faucet has a little drip | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-217 | 🔴 | AC works fine but I want it cleaned | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-218 | 🔴 | One outlet in the guest room isn't working | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-219 | 🔴 | Estimate for a new AC sometime | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-220 | 🔴 | Pre-season tune-up | false | 0/1 | 0/1 blocked (judge-non-emergency interpretation) |
| C-221 | 🟡 | Toilet won't flush | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-222 | 🟡 | AC isn't cooling super well lately | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-223 | 🟡 | Water heater isn't producing hot water | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-224 | 🟡 | Heater stopped working, it's 40° outside | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-225 | 🟡 | Drain cleaning today, kind of urgent | borderline | 1/3 | 1/3 blocked (judge-non-emergency interpretation) |
| C-226 | 🟡 | Need plumber ASAP for clogged sink | borderline | 1/3 | 1/3 blocked (judge-non-emergency interpretation) |
| C-227 | 🟡 | AC vents are weak | borderline | 1/3 | 1/3 blocked (judge-non-emergency interpretation) |
| C-228 | 🟡 | Slow leak under sink, not bad yet | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-229 | 🟡 | Active leak under sink | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |
| C-230 | 🟡 | Just an emergency really, please come | borderline | 0/3 | 0/3 blocked (judge-non-emergency interpretation) |

## Time spent

- Total wall-clock: ~62.1 min (3728 s sum of per-test timings)
- Test kinds: {'create_via_template': 5, 'skip': 56, 'create_via_prompt': 144, 'chat': 260, 'toggle_rule': 5, 'judge_calibration': 30}
