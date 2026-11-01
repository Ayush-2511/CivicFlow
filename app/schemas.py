"""Universal data contracts for CivicFlow.

Every module communicates through these Pydantic models.
Rule: Do not change these contracts without team consensus.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Operator(str, Enum):
    """Supported operators for deterministic condition evaluation."""
    LT = "lt"        # Less than (<)
    LTE = "lte"      # Less than or equal to (<=)
    GT = "gt"        # Greater than (>)
    GTE = "gte"      # Greater than or equal to (>=)
    EQ = "eq"        # Equals (==)
    NEQ = "neq"      # Not equals (!=)
    IN = "in"        # Membership in a list/collection
    NOT_IN = "not_in"# Not in collection


class Field_(str, Enum):
    """Controlled vocabulary shared between interview generation and the rule engine."""
    AGE = "age"
    ANNUAL_INCOME = "annual_income"
    LAND_HECTARES = "land_hectares"
    STATE = "state"
    CATEGORY = "category"           # e.g., General, OBC, SC, ST, EWS
    GENDER = "gender"               # e.g., Male, Female, Other
    OCCUPATION = "occupation"       # e.g., Farmer, Artisan, Student
    IS_FARMER = "is_farmer"
    IS_STUDENT = "is_student"
    HAS_DISABILITY = "has_disability"
    BUSINESS_TYPE = "business_type" # e.g., Micro, Small, Medium, Retail
    ANNUAL_TURNOVER = "annual_turnover"
    EMPLOYEES = "employees"


class AudienceType(str, Enum):
    """Target persona for the policy explainer."""
    CITIZEN = "citizen"
    BUSINESS = "business"


class VerdictStatus(str, Enum):
    """Deterministic eligibility verdict status."""
    YES = "YES"
    NO = "NO"
    MAYBE = "MAYBE"


class Clause(BaseModel):
    """Atomic indexed clause extracted from the official policy document."""
    id: str                         # Stable ID, e.g. "doc1-p3-c12"
    doc_id: str                     # SHA-256 hash or identifier of source document
    page: int                       # 1-indexed page number
    text: str                       # Full verbatim clause text


class Cited(BaseModel):
    """Base class for extracted facts that carry mandatory clause attribution."""
    clause_id: str
    quote: str                      # Exact substring of the source clause text


class Condition(Cited):
    """A single eligibility criterion extracted from the document."""
    field: Field_
    operator: Operator
    value: float | str | list[str]
    unit: str | None = None         # e.g. "hectares", "INR", "years"


class Benefit(Cited):
    """A tangible welfare benefit or grant provided by the scheme."""
    description: str
    amount: float | None = None
    frequency: str | None = None    # "yearly", "monthly", "one-time", etc.


class Obligation(Cited):
    """A compliance requirement, application step, or duty for citizen/business."""
    description: str
    deadline: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    apply_at: str | None = None     # Where to submit/register (e.g. "CSC portal", "DIC office")


class Scheme(BaseModel):
    """Complete structured representation of a policy, act, or scheme."""
    doc_id: str
    title: str
    audience: AudienceType = AudienceType.CITIZEN
    summary: str = ""
    benefits: list[Benefit] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    uncertain: list[str] = Field(default_factory=list)  # Clauses/rules needing clarification
    confidence: float = 1.0


class UserProfile(BaseModel):
    """Validated profile answers supplied by the user during the interview."""
    answers: dict[Field_, Any] = Field(default_factory=dict)

    def get(self, field: Field_, default: Any = None) -> Any:
        return self.answers.get(field, default)

    def set(self, field: Field_, value: Any) -> None:
        self.answers[field] = value

    def __contains__(self, field: Field_) -> bool:
        return field in self.answers


class Reason(BaseModel):
    """Explanation of a single evaluated condition in the verdict."""
    condition: Condition
    passed: bool | None             # True: passed, False: failed, None: missing answer
    explanation: str | None = None  # Human-readable breakdown of the evaluation


class Verdict(BaseModel):
    """Deterministic eligibility decision produced by the rule engine."""
    status: VerdictStatus           # YES, NO, or MAYBE
    reasons: list[Reason]
    missing_fields: list[Field_] = Field(default_factory=list)
    summary: str = ""


class Segment(BaseModel):
    """Sentence or paragraph in the explainer, tagged with source citations."""
    text: str                       # Already in the target localized language
    clause_ids: list[str] = Field(default_factory=list)
    audio_url: str | None = None    # URL/path to synthesized audio snippet


class Explainer(BaseModel):
    """Complete voice explainer and action checklist in the target language."""
    language: str                   # ISO 639-1 code (e.g., "hi", "en", "mr")
    verdict_segment: Optional[Segment] = None  # Dedicated regional voice for personal eligibility verdict
    segments: list[Segment] = Field(default_factory=list)  # Comprehensive scheme policy explanation
    checklist: list[str] = Field(default_factory=list)
    audio_urls: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    """A minimal interview question dynamically generated for a missing field."""
    field: Field_
    question_text: str
    input_type: str = "number"      # "number", "text", "choice", "boolean"
    options: list[str] | None = None
    unit: str | None = None
    default_value: Any = None


class TraceEntry(BaseModel):
    """Observability trace entry logged per node execution."""
    node: str
    status: str                     # "ok", "retry", "error", "skipped"
    ms: float                       # Execution time in milliseconds
    retries: int = 0
    details: str | None = None


class SectionExtraction(BaseModel):
    """Structured extraction output for a section/group of clauses."""
    title: str = ""
    audience: AudienceType = AudienceType.CITIZEN
    benefits: list[Benefit] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    uncertain: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Result of LLM verification re-check pass on an extracted cited fact."""
    is_supported: bool
    reason: str
    corrected_quote: str | None = None
