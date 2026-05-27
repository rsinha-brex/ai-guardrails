"""Rule parameter models, discriminated union, and outcome types."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.engine.expressions import Expression


# --------------------------------------------------------------------------- #
# Enums shared by rule parameters
# --------------------------------------------------------------------------- #


class Weekday(str, Enum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


# Service-type vocabulary is intentionally open-ended. Rules name granular
# variants like "hvac_install" / "roof_replacement" / "bathroom_remodel" /
# "panel_upgrade" / "ev_charger_install" / "pool_install" / "fence_install" /
# "garage_door_repair" / "irrigation_install" / etc. The 10-business seed
# defines its own per-business catalogs, and the compile step is allowed to
# produce any string here.
ServiceType = str


class StateField(str, Enum):
    ADDRESS_ZIP = "address_zip"
    ADDRESS = "address"
    PROPERTY_YEAR_BUILT = "property_year_built"
    HOA_GOVERNED = "hoa_governed"
    IS_HOMEOWNER = "is_homeowner"
    IS_EXISTING_CUSTOMER = "is_existing_customer"
    REPORTED_ISSUE = "reported_issue"
    IS_EMERGENCY = "is_emergency"


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str  # "HH:MM" 24-hour
    end: str    # "HH:MM" 24-hour


# --------------------------------------------------------------------------- #
# Per-rule-type parameter models
# --------------------------------------------------------------------------- #


class _ParamsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BusinessHoursParameters(_ParamsBase):
    timezone: str
    hours_by_day: dict[Weekday, TimeRange]
    closed_days: list[Weekday] = Field(default_factory=list)
    block_message: str


class ServiceAreaZipParameters(_ParamsBase):
    allowed_zips: list[str]
    denied_zips: list[str] = Field(default_factory=list)
    block_message: str


class ServicesOfferedParameters(_ParamsBase):
    allowed_services: list[ServiceType]
    block_message: str


class CustomerEligibilityParameters(_ParamsBase):
    homeowner_required: bool = False
    exclude_renters: bool = False
    membership_required: bool = False
    block_message: str
    required_state_fields: list[StateField] = Field(default_factory=list)
    # Optional service-type filter: when set, the rule only fires when
    # `args.service_type` is in this list. Mirrors the lead_time_minimum
    # pattern. Lets owners scope eligibility (e.g. "homeowner required for
    # installs") instead of having it fire on every booking.
    applies_to_service_types: list[ServiceType] | None = None


class LeadTimeParameters(_ParamsBase):
    minimum_hours: int
    applies_to_service_types: list[ServiceType] | None = None  # None = all
    bypass_if_state_field: StateField | None = None
    bypass_if_state_value: Any = None
    block_message: str


class ConditionalBlockParameters(_ParamsBase):
    trigger: Expression
    required_precondition: Expression | None = None
    block_message: str


class OutputConstraintParameters(_ParamsBase):
    instruction: str
    severity: Literal["guidance", "must"] = "guidance"


# --------------------------------------------------------------------------- #
# BaseRule discriminated union
# --------------------------------------------------------------------------- #


class _RuleBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    applies_when_description: str = ""
    applies_to_tools: list[str] = Field(default_factory=list)
    enforcement_mode: Literal["block", "warn"] = "block"
    priority: int = 100
    is_active: bool = True
    source_prompt: str | None = None


class BusinessHoursRule(_RuleBase):
    rule_type: Literal["business_hours"] = "business_hours"
    parameters: BusinessHoursParameters


class ServiceAreaZipRule(_RuleBase):
    rule_type: Literal["service_area_zip"] = "service_area_zip"
    parameters: ServiceAreaZipParameters


class ServicesOfferedRule(_RuleBase):
    rule_type: Literal["services_offered"] = "services_offered"
    parameters: ServicesOfferedParameters


class CustomerEligibilityRule(_RuleBase):
    rule_type: Literal["customer_eligibility"] = "customer_eligibility"
    parameters: CustomerEligibilityParameters


class LeadTimeRule(_RuleBase):
    rule_type: Literal["lead_time_minimum"] = "lead_time_minimum"
    parameters: LeadTimeParameters


class ConditionalBlockRule(_RuleBase):
    rule_type: Literal["conditional_block"] = "conditional_block"
    parameters: ConditionalBlockParameters


class OutputConstraintRule(_RuleBase):
    rule_type: Literal["output_constraint"] = "output_constraint"
    parameters: OutputConstraintParameters


BaseRule = Annotated[
    Union[
        BusinessHoursRule,
        ServiceAreaZipRule,
        ServicesOfferedRule,
        CustomerEligibilityRule,
        LeadTimeRule,
        ConditionalBlockRule,
        OutputConstraintRule,
    ],
    Field(discriminator="rule_type"),
]


# --------------------------------------------------------------------------- #
# Compile-step output (rule produced by the LLM compiler)
# --------------------------------------------------------------------------- #


class CompiledRule(BaseModel):
    """A rule definition emitted by the compile agent. Validated server-side."""

    model_config = ConfigDict(extra="forbid")

    rule_type: Literal[
        "business_hours",
        "service_area_zip",
        "services_offered",
        "customer_eligibility",
        "lead_time_minimum",
        "conditional_block",
        "output_constraint",
    ]
    name: str
    description: str
    applies_when_description: str = ""
    applies_to_tools: list[str] = Field(default_factory=list)
    enforcement_mode: Literal["block", "warn"] = "block"
    priority: int = 100
    parameters: dict[str, Any]
    source_prompt: str
    rationale: str = ""
    # Tiered output: the compile agent can mark a rule as a draft when the
    # rule type is correct but specific parameters need the owner's input
    # (e.g. "Seattle metro" → service_area_zip with empty allowed_zips, owner
    # supplies the actual ZIP list). The UI surfaces draft rules with an
    # "owner action needed" banner. `concrete` is the default.
    confidence: Literal["concrete", "draft"] = "concrete"
    draft_gaps: list[str] = Field(default_factory=list)


class CompileFailure(BaseModel):
    """Compiler couldn't produce a rule; surfaces clarifying questions."""

    model_config = ConfigDict(extra="forbid")
    suggested_clarifications: list[str]
    rationale: str = ""


# --------------------------------------------------------------------------- #
# Rule outcome types (returned by per-rule evaluators)
# --------------------------------------------------------------------------- #


class OutcomePass(BaseModel):
    outcome: Literal["pass"] = "pass"


class OutcomeBlock(BaseModel):
    outcome: Literal["block"] = "block"
    block_message: str
    internal_reason: str = ""


class OutcomeNeedsInfo(BaseModel):
    outcome: Literal["needs_info"] = "needs_info"
    required_fields: list[str]
    user_facing_message: str = ""


RuleOutcome = OutcomePass | OutcomeBlock | OutcomeNeedsInfo


class RuleSummary(BaseModel):
    """Lightweight rule shape returned by GET /rules — includes computed fields."""

    id: UUID
    business_id: UUID
    rule_type: str
    name: str
    description: str
    applies_when_description: str
    parameters: dict[str, Any]
    applies_to_tools: list[str]
    enforcement_mode: str
    priority: int
    is_active: bool
    source_prompt: str | None
    test_case_count: int = 0
    test_passing: int = 0
    test_failing: int = 0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def parse_rule(raw: dict[str, Any]) -> Any:
    """Parse a raw dict into the right concrete rule type via the discriminator."""
    from pydantic import TypeAdapter

    return TypeAdapter(BaseRule).validate_python(raw)
