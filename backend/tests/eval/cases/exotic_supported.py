"""Exotic-but-supported rule patterns (E1–E10).

These exercise machinery that the engine technically already supports but
that wasn't covered by the basic family A/B cases — deeply nested expressions,
regex, contains, time-relative bounds, negation rules, mutually exclusive
rule sets, judge-only rules, composed judges, override-by-precondition,
whitelist-via-composition.
"""
from __future__ import annotations

from app.engine.expressions import FakeJudgeClient
from tests.eval.businesses import _snap
from tests.eval.framework import (
    BlockedByRule,
    EvalCase,
    FiredRuleCount,
    OutcomeIs,
    register,
)
from tests.eval.taxonomy import Family, Group, InputShape

# E1 — time-relative trigger (less than 24h OR more than 90 days out)
register(
    EvalCase(
        id="EV-EX-001",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E1 too-far-out booking → blocked via gt(args.days_out, 90)",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "gt",
                        "field": "args.days_out",
                        "value": 90,
                    },
                    "block_message": "More than 90 days out — too far ahead.",
                },
                name="Far-future block",
                priority=140,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2027-06-16",
                "time": "10:00",
                "service_type": "hvac",
                "days_out": 365,
            },
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("Far-future")],
    )
)


# E2 — negation rule: block all bookings *except* maintenance on weekends
register(
    EvalCase(
        id="EV-EX-002",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E2 negation: weekend booking that ISN'T maintenance → blocked",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {
                                "op": "in",
                                "field": "args.weekday",
                                "value": ["sat", "sun"],
                            },
                            {
                                "op": "not",
                                "child": {
                                    "op": "eq",
                                    "field": "args.service_type",
                                    "value": "maintenance",
                                },
                            },
                        ],
                    },
                    "block_message": "Only maintenance on weekends.",
                },
                name="Weekend non-maintenance block",
                priority=160,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-21",  # Sunday
                "time": "10:00",
                "weekday": "sun",
                "service_type": "hvac",
            },
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("Weekend")],
    )
)

register(
    EvalCase(
        id="EV-EX-003",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E2 negation: weekend MAINTENANCE → accepted (escape)",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {
                                "op": "in",
                                "field": "args.weekday",
                                "value": ["sat", "sun"],
                            },
                            {
                                "op": "not",
                                "child": {
                                    "op": "eq",
                                    "field": "args.service_type",
                                    "value": "maintenance",
                                },
                            },
                        ],
                    },
                    "block_message": "Only maintenance on weekends.",
                },
                name="Weekend non-maintenance block",
                priority=160,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-21",
                "time": "10:00",
                "weekday": "sun",
                "service_type": "maintenance",
            },
        },
        assertions=[OutcomeIs("accepted")],
    )
)


# E3 — regex match: profanity in reported issue → block
register(
    EvalCase(
        id="EV-EX-004",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E3 regex on reported_issue → block when profanity present",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "matches_regex",
                        "field": "state.reported_issue",
                        "value": r"\b(damn|hell)\b",
                    },
                    "block_message": "Let's escalate this to a human.",
                },
                name="Profanity escalate",
                priority=140,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
        },
        state={"reported_issue": "the damn pipe burst again"},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Profanity")],
    )
)


# E4 — string contains
register(
    EvalCase(
        id="EV-EX-005",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E4 contains: address has 'Apt' substring → block (likely renter)",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "contains",
                        "field": "state.address",
                        "value": "Apt",
                    },
                    "block_message": "Apartment work needs landlord coordination.",
                },
                name="Apartment heuristic",
                priority=120,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "plumbing"},
        },
        state={"address": "123 Main St, Apt 5B"},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Apartment")],
    )
)


# E5 — deeply nested logic: (HVAC AND after 3 PM) OR (Plumbing AND after 4 PM)
register(
    EvalCase(
        id="EV-EX-006",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G2,
        title="E5 nested any_of/all_of: HVAC at 3:30 PM → blocked",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "any_of",
                        "children": [
                            {
                                "op": "all_of",
                                "children": [
                                    {"op": "eq", "field": "args.service_type", "value": "hvac"},
                                    {"op": "gte", "field": "args.time", "value": "15:00"},
                                ],
                            },
                            {
                                "op": "all_of",
                                "children": [
                                    {"op": "eq", "field": "args.service_type", "value": "plumbing"},
                                    {"op": "gte", "field": "args.time", "value": "16:00"},
                                ],
                            },
                        ],
                    },
                    "block_message": "Late-day install/plumbing block.",
                },
                name="Late-day nested",
                priority=150,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "15:30", "service_type": "hvac"},
        },
        assertions=[OutcomeIs("blocked"), BlockedByRule("nested")],
    )
)


# E6 — mutually exclusive rules don't crash
register(
    EvalCase(
        id="EV-EX-007",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G4,
        title="E6 contradictory rule set ('only Mon' + 'only Wed' for hvac) → both fire",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "hvac"},
                            {"op": "neq", "field": "args.weekday", "value": "mon"},
                        ],
                    },
                    "block_message": "HVAC only on Mondays.",
                },
                name="Only-Mon HVAC",
                priority=151,
            ),
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "all_of",
                        "children": [
                            {"op": "eq", "field": "args.service_type", "value": "hvac"},
                            {"op": "neq", "field": "args.weekday", "value": "wed"},
                        ],
                    },
                    "block_message": "HVAC only on Wednesdays.",
                },
                name="Only-Wed HVAC",
                priority=152,
            ),
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {
                "date": "2026-06-16",
                "time": "10:00",
                "service_type": "hvac",
                "weekday": "tue",
            },
        },
        assertions=[OutcomeIs("blocked"), FiredRuleCount(2)],
    )
)


# E7 — judge-only rule (using FakeJudgeClient with deterministic answer)
register(
    EvalCase(
        id="EV-EX-008",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="E7 judge-only rule: judge says 'offensive' → block",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "llm_judge",
                        "field": "state.reported_issue",
                        "question": "Is the message offensive?",
                    },
                    "block_message": "Let's get a human on this one.",
                },
                name="Offensive escalate",
                priority=130,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
            "judge": FakeJudgeClient(answers={"offensive": True}),
        },
        state={"reported_issue": "Your service is offensive and slow."},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Offensive")],
    )
)


# E8 — composed judges
register(
    EvalCase(
        id="EV-EX-009",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G6,
        title="E8 composed judges: any_of[offensive, threatening] → block on second judge",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "trigger": {
                        "op": "any_of",
                        "children": [
                            {
                                "op": "llm_judge",
                                "field": "state.reported_issue",
                                "question": "Is the message offensive?",
                            },
                            {
                                "op": "llm_judge",
                                "field": "state.reported_issue",
                                "question": "Is the message threatening?",
                            },
                        ],
                    },
                    "block_message": "Escalate to human.",
                },
                name="Composed judges",
                priority=130,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
            "judge": FakeJudgeClient(answers={"offensive": False, "threatening": True}),
        },
        state={"reported_issue": "I'll come down there if you don't book me."},
        assertions=[OutcomeIs("blocked"), BlockedByRule("Composed")],
    )
)


# E9 — override-by-precondition: rule only applies when waiver acknowledged
register(
    EvalCase(
        id="EV-EX-010",
        family=Family.EX,
        input_shape=InputShape.S1,
        group=Group.G3,
        title="E9 override-by-precondition: large-job rule only fires when state.is_existing_customer=true",
        runner_kind="engine",
        rules=[
            _snap(
                "conditional_block",
                {
                    "required_precondition": {
                        "op": "eq",
                        "field": "state.is_existing_customer",
                        "value": True,
                    },
                    "trigger": {
                        "op": "neq",
                        "field": "state.is_homeowner",
                        "value": True,
                    },
                    "block_message": "Existing customers must be the homeowner.",
                },
                name="Existing-customer homeowner gate",
                priority=140,
            )
        ],
        inputs={
            "tool_name": "book_appointment",
            "args": {"date": "2026-06-16", "time": "10:00", "service_type": "hvac"},
        },
        state={"is_existing_customer": False, "is_homeowner": False},
        assertions=[OutcomeIs("accepted")],  # precondition false → rule doesn't apply
    )
)
