"""
Lightweight routing and intent models for agentic orchestration.

These are deliberately simpler than the full design spec, but keep the same
shape so we can evolve without breaking callers.
"""
from __future__ import annotations

from typing import List, Literal, Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field


TaskType = Literal[
    "status",
    "prioritization",
    "trend",
    "root_cause",
    "recommendation",
    "definition",
    "procedure",
    "data_request",
]

EntityType = Literal[
    "item_class",
    "discipline",
    "tag",
    "asset",
    "facility",
    "kpi",
    "risk_term",
    "standard",
]

DisciplineName = Literal[
    "topsides",
    "fuims",
    "psv",
    "subsea",
    "pipeline",
    "corrosion",
    "methods",
    "generic",
]


class IntentEntity(BaseModel):
    type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class IntentDateRange(BaseModel):
    mode: Literal["none", "explicit", "implicit"] = "none"
    start: Optional[str] = None  # YYYY-MM-DD
    end: Optional[str] = None


class ScopeFilter(BaseModel):
    field: str
    op: Literal["eq", "in", "gte", "lte", "contains"]
    value: Any


class QueryScope(BaseModel):
    facility: List[str] = []
    asset: List[str] = []
    item_classes: List[str] = []
    date_range: IntentDateRange = Field(default_factory=IntentDateRange)
    risk_focus: List[str] = []
    filters: List[ScopeFilter] = []


class EvidenceRequirements(BaseModel):
    needs_kpi: bool = True
    needs_item_rows: bool = True
    needs_history: bool = False
    needs_visual: bool = False
    needs_procedures_or_standards: bool = False


class AmbiguityInfo(BaseModel):
    score: float = Field(0.0, ge=0.0, le=1.0)
    reasons: List[str] = []


class QueryIntent(BaseModel):
    """Compact representation of what the user is asking."""

    query_id: str = Field(default_factory=lambda: str(uuid4()))
    raw_message: str
    task_types: List[TaskType] = []
    entities: List[IntentEntity] = []
    scope: QueryScope = Field(default_factory=QueryScope)
    evidence_requirements: EvidenceRequirements = Field(
        default_factory=EvidenceRequirements
    )
    ambiguity: AmbiguityInfo = Field(default_factory=AmbiguityInfo)


class RoutingReason(BaseModel):
    type: Literal["keyword", "mapping", "retrieval", "history_requirement", "safety"]
    detail: str


class EvidenceProbe(BaseModel):
    retrieved_item_count: int = 0
    mapped_coverage_pct: float = 0.0
    discipline_purity_pct: float = 0.0
    field_completeness_pct: float = 0.0


class RoutingSliceFilter(BaseModel):
    field: str
    op: Literal["eq", "in", "gte", "lte", "contains"]
    value: Any


class RoutingCandidate(BaseModel):
    discipline: DisciplineName
    score: float = 0.0
    reasons: List[RoutingReason] = []
    evidence_probe: EvidenceProbe = Field(default_factory=EvidenceProbe)
    slice_filters: List[RoutingSliceFilter] = []


class SelectedDiscipline(BaseModel):
    discipline: DisciplineName
    role: Literal["specialist", "synthesizer", "triage"] = "specialist"
    slice_filters: List[RoutingSliceFilter] = []


class UIExplain(BaseModel):
    routed_to: List[str] = []
    based_on: List[str] = []
    scope_applied: List[str] = []
    evidence_size: str = ""


class RoutingDecision(BaseModel):
    query_id: str
    mode: Literal["single", "multi", "clarify", "no_evidence"] = "single"
    candidates: List[RoutingCandidate] = []
    selected: List[SelectedDiscipline] = []
    ui_explain: UIExplain = Field(default_factory=UIExplain)
    clarifying_questions: List[str] = []


def make_empty_routing(raw_message: str) -> RoutingDecision:
    """Utility for creating a no-op routing decision when routing is skipped."""
    qi = QueryIntent(raw_message=raw_message)
    return RoutingDecision(
        query_id=qi.query_id,
        mode="clarify",
        candidates=[],
        selected=[],
        ui_explain=UIExplain(
            routed_to=[],
            based_on=["No routing performed"],
            scope_applied=[],
            evidence_size="0 items",
        ),
        clarifying_questions=[],
    )


# ---------------------------------------------------------------------------
# Keyword-scoring tables for parse_query_intent()
# ---------------------------------------------------------------------------

_DISCIPLINE_KEYWORDS: Dict[str, List[str]] = {
    "topsides": [
        "topsides", "topside", "pressure vessel", "vessel", "vii", "vie",
        "non-structural tank", "tank", "structure", "piping", "pipe",
    ],
    "fuims": [
        "fuims", "fire", "gas", "fire & gas", "fire and gas", "esd",
        "emergency shutdown", "shutdown", "safety system", "fu item",
        "instrumented", "monitoring",
    ],
    "psv": [
        "psv", "pressure safety", "relief valve", "safety valve",
        "relief", "overpressure", "set pressure",
    ],
    "subsea": [
        "subsea", "christmas tree", "xmas tree", "tree", "manifold",
        "umbilical", "subsurface",
    ],
    "pipeline": [
        "pipeline", "pigging", "pig", "ili", "intelligent pigging",
        "inline inspection", "pipeline inspection",
    ],
    "corrosion": [
        "corrosion", "corrosion monitoring", "coating", "cathodic",
        "cp", "cathodic protection", "ut", "wall thickness",
    ],
    "methods": [
        "method", "procedure", "standard", "specification", "compliance",
        "quality assurance", "qa", "qc",
    ],
}

_TASK_KEYWORDS: Dict[str, List[str]] = {
    "status":         ["status", "state", "current", "where", "progress"],
    "prioritization": ["priorit", "high risk", "urgent", "critical", "top", "worst", "most"],
    "trend":          ["trend", "over time", "history", "historical", "change"],
    "root_cause":     ["why", "cause", "root", "reason", "issue"],
    "recommendation": ["recommend", "suggest", "should", "action", "fix", "resolve"],
    "data_request":   ["show", "list", "give", "how many", "count", "total", "all"],
    "procedure":      ["procedure", "how to", "steps", "process", "method"],
    "definition":     ["what is", "define", "meaning", "explain"],
}

_RISK_KEYWORDS = ["high risk", "high-risk", "overdue", "sece", "critical", "urgent", "escalat"]
_FACILITY_KEYWORDS = {"gir", "dal", "paz", "clv"}


def parse_query_intent(message: str) -> QueryIntent:
    """
    Parse a user message into a structured QueryIntent.

    Uses keyword scoring — no LLM required — keeping latency near-zero.
    Returns a QueryIntent that the orchestrator uses to build a RoutingDecision.
    """
    msg = message.lower()

    # --- Task type detection ---
    task_types: List[TaskType] = []
    for t_type, keywords in _TASK_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            task_types.append(t_type)  # type: ignore[arg-type]
    if not task_types:
        task_types = ["data_request"]

    # --- Entity extraction ---
    entities: List[IntentEntity] = []

    # Disciplines
    for disc, keywords in _DISCIPLINE_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in msg]
        if hits:
            confidence = min(1.0, 0.5 + 0.1 * len(hits))
            entities.append(IntentEntity(
                type="discipline",
                value=disc,
                confidence=round(confidence, 2),
            ))

    # Risk terms
    for rk in _RISK_KEYWORDS:
        if rk in msg:
            entities.append(IntentEntity(type="risk_term", value=rk, confidence=0.9))

    # Facility
    for fac in _FACILITY_KEYWORDS:
        if fac in msg:
            entities.append(IntentEntity(type="facility", value=fac.upper(), confidence=1.0))

    # --- Scope ---
    risk_focus = [e.value for e in entities if e.type == "risk_term"]
    facilities = [e.value for e in entities if e.type == "facility"]
    item_classes = [e.value for e in entities if e.type == "discipline"]

    scope = QueryScope(
        facility=facilities,
        item_classes=item_classes,
        risk_focus=risk_focus,
    )

    # --- Evidence requirements ---
    evidence = EvidenceRequirements(
        needs_kpi=True,
        needs_item_rows=True,
        needs_history="trend" in task_types or "root_cause" in task_types,
        needs_procedures_or_standards="procedure" in task_types or "definition" in task_types,
    )

    # --- Ambiguity ---
    disc_entities = [e for e in entities if e.type == "discipline"]
    ambiguity_score = 0.0 if disc_entities else 0.6
    ambiguity_reasons = [] if disc_entities else ["No specific discipline detected"]

    return QueryIntent(
        raw_message=message,
        task_types=task_types,
        entities=entities,
        scope=scope,
        evidence_requirements=evidence,
        ambiguity=AmbiguityInfo(score=ambiguity_score, reasons=ambiguity_reasons),
    )


def build_routing_decision(intent: QueryIntent) -> RoutingDecision:
    """
    Convert a QueryIntent into a RoutingDecision.

    Scoring rules:
    - Direct discipline keyword match  → score += 0.5 + confidence bonus
    - Risk/SECE terms present          → score += 0.2 for safety disciplines (PSV, FUIMS)
    - Facility match                   → no change (all disciplines get same data)
    - No discipline entities at all    → route to ALL disciplines (mode=multi, score=0.3 each)
    """
    disc_entities = {e.value: e for e in intent.entities if e.type == "discipline"}
    risk_entities = [e for e in intent.entities if e.type == "risk_term"]

    candidates: List[RoutingCandidate] = []
    all_disciplines: List[str] = [
        "topsides", "fuims", "psv", "subsea", "pipeline", "corrosion", "methods"
    ]

    if disc_entities:
        # Score matched disciplines
        for disc, entity in disc_entities.items():
            if disc == "generic":
                continue
            score = 0.5 + entity.confidence * 0.4
            reasons = [RoutingReason(
                type="keyword",
                detail=f"Matched '{disc}' keywords with confidence {entity.confidence}"
            )]
            # Safety boost
            if disc in ("psv", "fuims") and risk_entities:
                score += 0.2
                reasons.append(RoutingReason(
                    type="safety",
                    detail="Safety discipline boosted due to risk/SECE terms"
                ))
            candidates.append(RoutingCandidate(
                discipline=disc,  # type: ignore[arg-type]
                score=round(min(score, 1.0), 3),
                reasons=reasons,
            ))
        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        mode: Literal["single", "multi", "clarify", "no_evidence"] = (
            "single" if len(candidates) == 1 else "multi"
        )
    else:
        # No specific discipline — broadcast to all
        for disc in all_disciplines:
            candidates.append(RoutingCandidate(
                discipline=disc,  # type: ignore[arg-type]
                score=0.3,
                reasons=[RoutingReason(type="mapping", detail="Broadcast: no specific discipline detected")],
            ))
        mode = "multi"

    # Build selected list from top-scoring candidates (score >= 0.3)
    threshold = 0.3
    selected = [
        SelectedDiscipline(discipline=c.discipline, role="specialist")
        for c in candidates if c.score >= threshold
    ]

    ui_explain = UIExplain(
        routed_to=[s.discipline for s in selected],
        based_on=[r.detail for c in candidates[:3] for r in c.reasons],
        scope_applied=[f"facility={f}" for f in intent.scope.facility]
                      + [f"risk={r}" for r in intent.scope.risk_focus[:2]],
        evidence_size=f"{len(selected)} discipline(s) selected",
    )

    return RoutingDecision(
        query_id=intent.query_id,
        mode=mode,
        candidates=candidates,
        selected=selected,
        ui_explain=ui_explain,
        clarifying_questions=[],
    )
