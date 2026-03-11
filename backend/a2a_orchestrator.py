"""
a2a_orchestrator.py
====================
Master multi-agent coordinator — public API: ``orchestrate()``.

Architecture
------------
1. parse_query_intent()  →  RoutingDecision  (which disciplines to invoke)
2. asyncio.gather()      →  parallel CrewAI discipline agents
3. AgentMessageBus       →  cross-discipline finding propagation
4. MasterInspector agent →  synthesises all reports into an executive summary

The ``orchestrate()`` coroutine is the single entry-point consumed by the
``/a2a/orchestrate`` FastAPI endpoint.  It replaces the sequential for-loop
in ``run_engineering_agents()`` with genuine parallel execution and
inter-agent communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from a2a_protocol import (
    AGENT_CARDS,
    A2AResponse,
    AgentMessageBus,
    OrchestratorReport,
    get_or_create_bus,
    release_bus,
)
from routing_models import (
    RoutingDecision,
    build_routing_decision,
    parse_query_intent,
)

logger = logging.getLogger(__name__)

# Optional CrewAI imports
try:
    from crewai import Agent, Crew, Process, Task
    from crewai.llm import LLM as CrewLLM
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    Agent = Task = Crew = Process = CrewLLM = None  # type: ignore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Model catalogue — maps frontend model_id → (provider, crewai_model, base_url_or_None)
# "openrouter" provider → OpenAI-compat API at openrouter.ai (uses OPENROUTER_API_KEY)
# "deepseek"   provider → DeepSeek native API (uses DEEPSEEK_API_KEY)
# "anthropic"  provider → Anthropic native via LiteLLM (uses ANTHROPIC_API_KEY)
# "gemini"     provider → Google Gemini via LiteLLM (uses GEMINI_API_KEY)
# ---------------------------------------------------------------------------
MODEL_CATALOGUE: Dict[str, Dict[str, str]] = {
    # ── OpenRouter-proxied models ──────────────────────────────────────────
    "openrouter/minimax/minimax-m2.5": {"provider": "openrouter", "model": "minimax/minimax-m2.5"},
    "openrouter/gpt-4o-mini":         {"provider": "openrouter", "model": "gpt-4o-mini"},
    "openrouter/gpt-4o":              {"provider": "openrouter", "model": "gpt-4o"},
    # ── DeepSeek standalone ────────────────────────────────────────────────
    "deepseek/deepseek-chat":         {"provider": "deepseek",   "model": "deepseek-chat"},
    "deepseek/deepseek-reasoner":     {"provider": "deepseek",   "model": "deepseek-reasoner"},
    # ── Anthropic standalone ───────────────────────────────────────────────
    "anthropic/claude-haiku-3-5":     {"provider": "anthropic",  "model": "claude-haiku-3-5-20241022"},
    "anthropic/claude-sonnet-4-5":    {"provider": "anthropic",  "model": "claude-sonnet-4-5-20250929"},
    "anthropic/claude-opus-4-5":      {"provider": "anthropic",  "model": "claude-opus-4-5"},
    # ── Google Gemini standalone ───────────────────────────────────────────
    "gemini/gemini-2.0-flash":        {"provider": "gemini",     "model": "gemini/gemini-2.0-flash"},
    "gemini/gemini-1.5-pro":          {"provider": "gemini",     "model": "gemini/gemini-1.5-pro"},
    "gemini/gemini-1.5-flash":        {"provider": "gemini",     "model": "gemini/gemini-1.5-flash"},
}

# Default model used when none is specified in the request
_DEFAULT_MODEL_ID = "deepseek/deepseek-chat"


def _build_llm(model_id: Optional[str] = None) -> Optional[Any]:
    """Return a crewai.LLM instance for the requested model, or None.

    model_id must be one of the keys in MODEL_CATALOGUE.
    Defaults to _DEFAULT_MODEL_ID (openrouter/gpt-4o-mini) if not supplied.

    Provider routing:
      openrouter → CrewAI native OpenAI provider + OpenRouter base_url
      deepseek   → CrewAI native OpenAI provider + DeepSeek base_url
      anthropic  → LiteLLM "anthropic/" prefix path
      gemini     → LiteLLM "gemini/" prefix path
    """
    if not AI_AVAILABLE or CrewLLM is None:
        return None

    mid = (model_id or _DEFAULT_MODEL_ID).strip()
    entry = MODEL_CATALOGUE.get(mid)
    if entry is None:
        logger.warning(f"_build_llm: unknown model_id '{mid}', falling back to {_DEFAULT_MODEL_ID}")
        mid = _DEFAULT_MODEL_ID
        entry = MODEL_CATALOGUE[mid]

    provider = entry["provider"]
    model    = entry["model"]
    temp     = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    max_tok  = int(os.getenv("LLM_MAX_TOKENS", "1500"))

    try:
        if provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY")
            if not key:
                logger.warning("_build_llm: OPENROUTER_API_KEY not set")
                return None
            os.environ.setdefault("OPENAI_API_KEY", key)
            return CrewLLM(
                model=model,
                api_key=key,
                base_url="https://openrouter.ai/api/v1",
                temperature=temp,
                max_tokens=max_tok,
            )

        elif provider == "deepseek":
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                logger.warning("_build_llm: DEEPSEEK_API_KEY not set")
                return None
            os.environ.setdefault("OPENAI_API_KEY", key)
            return CrewLLM(
                model=model,
                api_key=key,
                base_url="https://api.deepseek.com/v1",
                temperature=temp,
                max_tokens=max_tok,
            )

        elif provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                logger.warning("_build_llm: ANTHROPIC_API_KEY not set")
                return None
            # LiteLLM path: "anthropic/<model>" prefix triggers litellm routing
            return CrewLLM(
                model=f"anthropic/{model}",
                api_key=key,
                temperature=temp,
                max_tokens=max_tok,
            )

        elif provider == "gemini":
            key = os.getenv("GEMINI_API_KEY")
            if not key:
                logger.warning("_build_llm: GEMINI_API_KEY not set")
                return None
            # LiteLLM path: "gemini/<model>" prefix triggers litellm routing
            return CrewLLM(
                model=model,
                api_key=key,
                temperature=temp,
                max_tokens=max_tok,
            )

        else:
            logger.warning(f"_build_llm: unhandled provider '{provider}'")
            return None

    except Exception as exc:
        logger.warning(f"_build_llm: crewai.LLM init failed for '{mid}' — {exc}")
        return None


def _detect_cross_discipline_findings(
    reports: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Inspect completed discipline reports for items that belong to ANOTHER
    discipline — a genuine cross-discipline risk scenario.

    Examples:
    - A corrosion finding on a PSV body → PSV + Corrosion risk
    - A topsides vessel with Fire & Gas association → Topsides + FUIMS risk
    """
    from engineering_agents import DISCIPLINE_CATEGORIES

    cross = []
    for source_disc, report_data in reports.items():
        source_items = report_data.get("critical_items", [])
        for item in source_items:
            tag = item.get("tag_id", "")
            # Simple heuristic: check if tag prefix maps to a different discipline
            for target_disc, categories in DISCIPLINE_CATEGORIES.items():
                if target_disc == source_disc:
                    continue
                for cat in categories:
                    cat_abbrev = cat[:3].upper()
                    if cat_abbrev in tag.upper() and cat_abbrev not in ("", "N/A"):
                        cross.append({
                            "type": "cross_discipline_risk",
                            "source_discipline": source_disc,
                            "target_discipline": target_disc,
                            "tag_id": tag,
                            "risk": item.get("risk", "Unknown"),
                            "days_overdue": item.get("days_overdue", 0),
                            "sece": item.get("sece", False),
                            "severity": "High" if item.get("sece") or item.get("days_overdue", 0) > 90 else "Medium",
                            "finding": (
                                f"{source_disc.title()} agent flagged {tag} "
                                f"({item.get('risk', '?')} risk, "
                                f"{item.get('days_overdue', 0)} days overdue) — "
                                f"may also involve {target_disc} scope."
                            ),
                        })
    # Deduplicate by tag_id + source + target
    seen = set()
    unique = []
    for c in cross:
        key = (c["tag_id"], c["source_discipline"], c["target_discipline"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


async def _run_one_discipline(
    discipline: str,
    items: List[Dict[str, Any]],
    bus: AgentMessageBus,
    site: Optional[str] = None,
    model_id: Optional[str] = None,
) -> A2AResponse:
    """
    Run a single discipline agent and publish cross-discipline findings
    to the message bus.
    """
    from engineering_agents import (
        DISCIPLINE_CATEGORIES,
        _calculate_kpi_snapshot,
        _create_agent,
        _create_task,
        _filter_items_by_category,
        _log_agent_trace,
        _memory_push,
        _prioritize_items,
        _summarize_items_for_prompt,
        _validate_report_payload,
    )

    t0 = time.monotonic()
    card = AGENT_CARDS.get(discipline)
    if card is None:
        return A2AResponse(
            task_id=str(uuid.uuid4()),
            agent=discipline,
            discipline=discipline,
            status="failed",
            text=f"No AgentCard found for discipline: {discipline}",
        )

    categories = DISCIPLINE_CATEGORIES.get(discipline, [])
    filtered = _filter_items_by_category(items, categories)
    kpi = _calculate_kpi_snapshot(filtered)

    fallback_report = {
        "summary": (
            f"{kpi['total']} {discipline} items: "
            f"{kpi['high_risk']} high-risk, {kpi['backlog_count']} in backlog."
        ),
        "key_findings": [
            f"Total: {kpi['total']} items",
            f"High risk: {kpi['high_risk']}",
            f"SECE: {kpi['sece_count']}",
        ],
        "recommendations": [
            "Prioritise high-risk SECE items",
            "Review overdue items immediately",
        ],
        "critical_items": [
            {
                "tag_id": it.get("Tag", "N/A"),
                "risk": "High" if it.get("Days in Backlog", 0) > 90 else "Medium",
                "days_overdue": it.get("Days in Backlog", 0),
                "sece": it.get("SECE", False),
            }
            for it in sorted(filtered, key=lambda x: x.get("Days in Backlog", 0), reverse=True)[:5]
        ],
        "trends": f"{kpi['completion_rate']}% completion rate",
    }

    report = fallback_report
    ai_used = False

    llm = _build_llm(model_id)
    if llm and AI_AVAILABLE and filtered:
        try:
            disc_configs = {
                "topsides": {"role": "Topsides Engineer",
                             "backstory": "You oversee topside integrity for pressure vessels, tanks, structures, and piping. You blend SECE focus with production realities to burn down overdue inspections."},
                "fuims":    {"role": "FUIMS Engineer",
                             "backstory": "You specialize in fire and utility instrumented systems, spotting silent failures, overdue proof tests, and missing verifications that undermine protection layers."},
                "psv":      {"role": "PSV Engineer",
                             "backstory": "Pressure protection authority with a track record of clearing PSV queues, validating set pressures, and coordinating outage windows to avoid overpressure scenarios."},
                "subsea":   {"role": "Subsea Engineer",
                             "backstory": "Subsea specialist experienced with trees, manifolds, and umbilicals who translates subsea findings into clear actions and campaign plans."},
                "pipeline": {"role": "Pipeline / ILI Engineer",
                             "backstory": "Pipeline integrity engineer skilled at planning and interpreting intelligent pigging, aligning anomaly responses with operations windows."},
                "corrosion":{"role": "Corrosion Engineer",
                             "backstory": "Corrosion control lead using probes, UT readings, and coatings assessments to prevent leaks and extend asset life."},
                "methods":  {"role": "Methods Engineer",
                             "backstory": "Methods engineer specialising in inspection procedures, standards compliance, and quality assurance across all disciplines."},
            }
            cfg = disc_configs.get(discipline, {"role": discipline.title(), "backstory": ""})
            agent = _create_agent(discipline, cfg["role"],
                                  f"Analyse {discipline} backlog and identify critical items.",
                                  cfg["backstory"], llm)
            task = _create_task(agent, _prioritize_items(filtered, 20), discipline, kpi)
            if agent and task:
                crew = Crew(agents=[agent], tasks=[task], verbose=False)
                result = await crew.kickoff_async()
                raw = (result.raw if hasattr(result, "raw") else str(result)).strip()
                # Strip markdown fences
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()
                parsed = json.loads(raw)
                if _validate_report_payload(parsed):
                    report = parsed
                    ai_used = True
                    _memory_push(discipline, parsed.get("summary", ""))
        except Exception as exc:
            logger.warning(f"[{discipline}] AI failed, using fallback: {exc}")

    _log_agent_trace(discipline, {"kpi": kpi, "ai_used": ai_used, "report": report})

    # Publish critical items to bus so other agents can react
    for crit in report.get("critical_items", []):
        if crit.get("sece") or crit.get("days_overdue", 0) > 90:
            await bus.publish(discipline, {
                "type": "critical_item",
                "target": "all",
                "tag_id": crit.get("tag_id"),
                "risk": crit.get("risk"),
                "days_overdue": crit.get("days_overdue", 0),
                "sece": crit.get("sece", False),
                "severity": "High",
                "finding": (
                    f"{discipline.title()} flagged {crit.get('tag_id')} — "
                    f"{crit.get('risk')} risk, {crit.get('days_overdue', 0)} days overdue."
                ),
            })

    duration_ms = int((time.monotonic() - t0) * 1000)
    return A2AResponse(
        task_id=str(uuid.uuid4()),
        agent=card.name,
        discipline=discipline,
        status="completed" if filtered else "no_data",
        text=report.get("summary", ""),
        kpi=kpi,
        report=report,
        ai_used=ai_used,
        duration_ms=duration_ms,
    )


async def _synthesise_with_llm(
    query: str,
    agent_responses: Dict[str, A2AResponse],
    cross_risks: List[Dict[str, Any]],
    overall_kpi: Dict[str, Any],
    model_id: Optional[str] = None,
) -> str:
    """
    Use a MasterInspector CrewAI agent to synthesise all discipline outputs
    into a coherent executive summary.
    """
    llm = _build_llm(model_id)
    if not llm or not AI_AVAILABLE:
        # Rule-based fallback
        lines = [f"Orchestrator synthesis for: '{query}'", ""]
        for disc, resp in agent_responses.items():
            if resp.status != "no_data":
                lines.append(f"**{disc.title()}**: {resp.text}")
        if cross_risks:
            lines.append("")
            lines.append(f"**Cross-discipline risks detected:** {len(cross_risks)}")
            for cr in cross_risks[:3]:
                lines.append(f"  • {cr['finding']}")
        return "\n".join(lines)

    # Compact report summaries for context
    summaries = {
        d: {
            "summary": r.text,
            "kpi": r.kpi,
            "critical_items": (r.report or {}).get("critical_items", [])[:3],
        }
        for d, r in agent_responses.items()
        if r.status != "no_data"
    }

    def _rule_based_summary() -> str:
        lines = [f"Orchestrator synthesis for: '{query}'", ""]
        for disc, resp in agent_responses.items():
            if resp.status != "no_data":
                lines.append(f"**{disc.title()}**: {resp.text}")
        if cross_risks:
            lines.append("")
            lines.append(f"**Cross-discipline risks detected:** {len(cross_risks)}")
            for cr in cross_risks[:3]:
                lines.append(f"  • {cr.get('finding', '')}")
        return "\n".join(lines)

    try:
        master = Agent(
            role="Master Inspection Coordinator",
            goal="Synthesise discipline-specific findings into an executive summary with cross-discipline risk escalations.",
            backstory=(
                "Senior offshore inspection coordinator with 25 years' experience across all "
                "disciplines. Expert at identifying systemic risks that span multiple engineering "
                "scopes and at communicating clearly to operations leadership."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        task = Task(
            description=f"""
USER QUERY: {query}

DISCIPLINE SUMMARIES:
{json.dumps(summaries, indent=2)}

CROSS-DISCIPLINE RISKS DETECTED ({len(cross_risks)}):
{json.dumps(cross_risks[:5], indent=2)}

OVERALL KPI:
{json.dumps(overall_kpi, indent=2)}

INSTRUCTIONS:
1. Write a terse executive summary (3-5 sentences) answering the user query.
2. Highlight the top 3 cross-discipline risks if any exist.
3. Give 2-3 concrete recommendations based on the data.
4. Reference Tag IDs and actual numbers — no generic statements.
5. Do NOT repeat KPI tables already shown — just reference key numbers.
""",
            expected_output="Concise executive summary with cross-discipline risk highlights and recommendations",
            agent=master,
        )

        crew = Crew(agents=[master], tasks=[task], verbose=False)
        result = await crew.kickoff_async()
        return (result.raw if hasattr(result, "raw") else str(result)).strip()
    except Exception as exc:
        logger.warning(f"MasterInspector synthesis failed, using rule-based fallback: {exc}")
        return _rule_based_summary()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def orchestrate(
    query: str,
    items: Optional[List[Dict[str, Any]]] = None,
    site: Optional[str] = None,
    session_id: Optional[str] = None,
    disciplines: Optional[List[str]] = None,
    model_id: Optional[str] = None,
) -> OrchestratorReport:
    """
    Main entry-point for A2A orchestration.

    Steps
    -----
    1. Parse intent + build routing decision
    2. Resolve which disciplines to invoke
    3. Load items from cache if not provided
    4. Run all selected discipline agents IN PARALLEL via asyncio.gather()
    5. Collect cross-discipline findings from AgentMessageBus
    6. Synthesise executive summary via MasterInspector agent
    7. Return OrchestratorReport

    Parameters
    ----------
    query       : User's natural-language question
    items       : Pre-loaded inspection items (optional, loaded from cache if absent)
    site        : Site filter for cache lookup (GIR / DAL / PAZ / CLV)
    session_id  : Caller-supplied session ID (generated if absent)
    disciplines : Override list of disciplines (skips routing if supplied)
    model_id    : Model catalogue key e.g. "openrouter/gpt-4o-mini" (default if absent)
    """
    t_start = time.monotonic()
    sid = session_id or str(uuid.uuid4())
    bus = get_or_create_bus(sid)

    # --- Step 1: Route ---
    if disciplines:
        # Caller explicitly specified disciplines — bypass routing
        intent = parse_query_intent(query)
        routing = build_routing_decision(intent)
        selected_disciplines = [d for d in disciplines if d in AGENT_CARDS]
        routing_mode = "single" if len(selected_disciplines) == 1 else "multi"
    else:
        intent = parse_query_intent(query)
        routing = build_routing_decision(intent)
        selected_disciplines = [s.discipline for s in routing.selected]
        routing_mode = routing.mode

    logger.info(f"[{sid}] Routing to {len(selected_disciplines)} disciplines: {selected_disciplines}")

    # --- Step 2: Load items ---
    if not items:
        from engineering_agents import _load_items_from_cache
        items = _load_items_from_cache(site=site) or []

    if not items:
        release_bus(sid)
        return OrchestratorReport(
            session_id=sid,
            query=query,
            disciplines_invoked=[],
            executive_summary="No cached backlog data available. Upload a file first.",
            routing_mode=routing_mode,  # type: ignore[arg-type]
        )

    # --- Step 3: Parallel execution ---
    tasks_coros = [
        _run_one_discipline(disc, items, bus, site, model_id)
        for disc in selected_disciplines
    ]
    responses_list: List[A2AResponse] = await asyncio.gather(*tasks_coros)
    agent_responses: Dict[str, A2AResponse] = {
        r.discipline: r for r in responses_list
    }

    # --- Step 4: Cross-discipline finding detection ---
    reports_raw = {
        disc: (resp.report or {})
        for disc, resp in agent_responses.items()
    }
    cross_risks = _detect_cross_discipline_findings(reports_raw)

    # Also collect high-severity bus messages
    bus_findings = bus.high_severity_findings()
    # Merge unique bus findings not already in cross_risks
    cross_tag_pairs = {(c["tag_id"], c["source_discipline"]) for c in cross_risks}
    for bf in bus_findings:
        key = (bf.get("tag_id", ""), bf.get("source", ""))
        if key not in cross_tag_pairs:
            cross_risks.append({
                "type": "bus_escalation",
                "source_discipline": bf.get("source"),
                "tag_id": bf.get("tag_id"),
                "risk": bf.get("risk"),
                "days_overdue": bf.get("days_overdue", 0),
                "sece": bf.get("sece", False),
                "severity": bf.get("severity", "High"),
                "finding": bf.get("finding", ""),
            })

    # --- Step 5: Overall KPI ---
    from engineering_agents import _calculate_kpi_snapshot
    overall_kpi = _calculate_kpi_snapshot(items)

    # --- Step 6: Synthesise ---
    summary = await _synthesise_with_llm(query, agent_responses, cross_risks, overall_kpi, model_id)

    total_ms = int((time.monotonic() - t_start) * 1000)
    ai_used = any(r.ai_used for r in agent_responses.values())

    release_bus(sid)

    return OrchestratorReport(
        session_id=sid,
        query=query,
        disciplines_invoked=selected_disciplines,
        parallel_execution=True,
        total_duration_ms=total_ms,
        cross_discipline_risks=cross_risks,
        executive_summary=summary,
        agent_responses=agent_responses,
        routing_mode=routing_mode,  # type: ignore[arg-type]
        ai_used=ai_used,
    )
