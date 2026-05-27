"""Taxonomy enums and coverage matrix builder.

Families A–H, input shapes S1–S25, and eval groups 1–10 are mirrored from
the catalog doc. The coverage matrix (Family × InputShape) is built by
walking the registered cases at session end and emitted into the report.
"""
from __future__ import annotations

from collections import Counter
from enum import Enum


class Family(str, Enum):
    A = "A"  # pure typed rules (deterministic)
    B = "B"  # group-scoped triggers (typed-rule semantics via conditional_block)
    C = "C"  # preconditioned rules (block-unless-state-X)
    D = "D"  # hybrid deterministic + LLM judge
    E = "E"  # output_constraint (system-prompt-injected)
    F = "F"  # cross-rule composition (multi-rule scenarios)
    G = "G"  # state-machine rules (multi-turn gathering)
    H = "H"  # output-shaping (agent communication style)
    EX = "EX"  # exotic-supported (E1–E10)
    DIS = "DIS"  # architecture-disposition (E11/E17/E18/E19/E20)
    ADV = "ADV"  # adversarial input shapes (S10–S22 illustrative)


class InputShape(str, Enum):
    S1 = "S1"   # well-formed canonical
    S2 = "S2"   # missing required fields
    S3 = "S3"   # implicit fields
    S4 = "S4"   # piecemeal across turns
    S5 = "S5"   # contradictory across turns
    S6 = "S6"   # ambiguous time references
    S7 = "S7"   # out-of-vocabulary services
    S8 = "S8"   # structured data dump
    S9 = "S9"   # free-text natural language
    S10 = "S10" # customer pushback
    S11 = "S11" # adversarial / prompt-injection
    S12 = "S12" # false information from customer
    S13 = "S13" # multi-issue requests
    S14 = "S14" # conditional / hypothetical
    S15 = "S15" # emoji / non-text
    S16 = "S16" # very long messages
    S17 = "S17" # very short messages
    S18 = "S18" # empty / whitespace
    S19 = "S19" # code-switched (multi-language)
    S20 = "S20" # profanity / hostile
    S21 = "S21" # distress signals
    S22 = "S22" # repeated identical requests
    S23 = "S23" # out-of-band requests (warranty, refunds)
    S24 = "S24" # test / dummy data
    S25 = "S25" # compile-step adversarial


class Group(int, Enum):
    G1 = 1  # engine correctness
    G2 = 2  # expression composition
    G3 = 3  # state machine integrity
    G4 = 4  # multi-rule aggregation
    G5 = 5  # compile-step structural correctness
    G6 = 6  # LLM judge mechanism
    G7 = 7  # agent rule citation behavior
    G8 = 8  # end-to-end conversation behavior
    G9 = 9  # compile-step semantic accuracy
    G10 = 10 # adversarial & edge cases


DETERMINISTIC_GROUPS = {Group.G1, Group.G2, Group.G3, Group.G4}


def coverage_matrix(cases: list) -> dict[tuple[str, str], int]:
    """Build a (family, input_shape) -> count mapping for the report."""
    cells: Counter[tuple[str, str]] = Counter()
    for c in cases:
        cells[(c.family.value, c.input_shape.value)] += 1
    return dict(cells)
