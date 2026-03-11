"""
Multi-Agent Engineering Analysis for Inspection Backlog
Discipline-specific crews analyze items by category and generate KPI reports
"""
import os
import json
import logging
import hashlib
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, date as _date, datetime as _dt, timedelta as _td
from dotenv import load_dotenv

# Load environment variables from backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Optional AI imports - gracefully handle if not installed
try:
    from langchain_openai import ChatOpenAI
    from crewai import Agent, Task, Crew, Process, LLM as CrewLLM
    from pydantic import BaseModel as _PydanticBase
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    ChatOpenAI = None
    Agent = None
    Task = None
    Crew = None
    Process = None
    CrewLLM = None
    _PydanticBase = None

logger = logging.getLogger(__name__)

# Response cache for instant repeated queries (in-memory for speed)
_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 3600  # 1 hour cache TTL

from database import get_cached_data, list_cached_files
from routing_models import (
    QueryIntent,
    RoutingDecision,
    RoutingCandidate,
    SelectedDiscipline,
    RoutingReason,
    EvidenceProbe,
    RoutingSliceFilter,
    UIExplain,
)


# -----------------
# LLM factory
# -----------------

def _build_crewai_llm(model_id: Optional[str] = None) -> Optional[Any]:
    """
    Build a crewai.LLM object for use with CrewAI agents.

    crewai.LLM uses LiteLLM under the hood, so model strings must follow
    LiteLLM's provider-prefix convention:
      - OpenRouter models : "openrouter/<model>"  e.g. "openrouter/minimax/mm-m2"
      - DeepSeek models   : "deepseek/<model>"    e.g. "deepseek/deepseek-chat"
      - Anthropic models  : "anthropic/<model>"   e.g. "anthropic/claude-haiku-3-5"
      - Gemini models     : "gemini/<model>"      e.g. "gemini/gemini-2.0-flash"

    The catalogue model_id already carries the provider prefix
    (e.g. "openrouter/minimax/mm-m2"), so we pass it directly.

    Falls back to OPENROUTER_MODEL env var (prepending "openrouter/" if needed).
    Returns None if CrewLLM is not imported.
    """
    if not AI_AVAILABLE or CrewLLM is None:
        return None

    temp = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    max_tok = int(os.getenv("LLM_MAX_TOKENS", "2000"))

    # Resolve which model_id / litellm string to use
    if model_id:
        litellm_model = model_id  # already prefixed, e.g. "openrouter/minimax/mm-m2"
    else:
        raw = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        # If env var has no provider prefix, assume openrouter
        if "/" not in raw or raw.startswith("openai/"):
            litellm_model = f"openrouter/{raw}"
        elif raw.startswith("openrouter/") or raw.startswith("deepseek/") \
                or raw.startswith("anthropic/") or raw.startswith("gemini/"):
            litellm_model = raw
        else:
            # bare model slug like "minimax/mm-m2" — assume openrouter
            litellm_model = f"openrouter/{raw}"

    # Choose the right API key based on provider prefix
    provider = litellm_model.split("/")[0]
    api_key_map = {
        "openrouter": os.getenv("OPENROUTER_API_KEY"),
        "deepseek":   os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "anthropic":  os.getenv("ANTHROPIC_API_KEY", "").strip(),
        "gemini":     os.getenv("GEMINI_API_KEY", "").strip(),
    }
    api_key = api_key_map.get(provider) or os.getenv("OPENROUTER_API_KEY")

    logger.debug(f"_build_crewai_llm: model={litellm_model}, provider={provider}")

    return CrewLLM(
        model=litellm_model,
        api_key=api_key,
        temperature=temp,
        max_tokens=max_tok,
    )


# -----------------
# Guardrails / helpers
# -----------------

def _validate_report_payload(payload: dict) -> bool:
    """Lightweight schema check for agent JSON output."""
    required_root = {"summary", "key_findings", "recommendations", "critical_items", "trends"}
    if not isinstance(payload, dict) or not required_root.issubset(payload.keys()):
        return False
    if not isinstance(payload.get("key_findings"), list) or not isinstance(payload.get("recommendations"), list):
        return False
    if not isinstance(payload.get("critical_items"), list):
        return False
    # Ensure critical items carry expected keys
    for item in payload.get("critical_items", [])[:5]:
        if not isinstance(item, dict):
            return False
        for field in ("tag_id", "risk", "days_overdue", "sece"):
            if field not in item:
                return False
    return True


class _AgentReportSchema(_PydanticBase if _PydanticBase else object):
    """Pydantic schema for CrewAI 1.x output_json enforcement."""
    summary: str = ""
    key_findings: list = []
    recommendations: list = []
    critical_items: list = []
    trends: str = ""


def _wrap_guardrail(task: "Task") -> "Task":
    """Attach a guardrail parser that enforces JSON structure with minimal retries.

    CrewAI 1.x: output_json expects a Pydantic model class (not a parser instance).
    """
    if not AI_AVAILABLE or _PydanticBase is None:
        return task
    task.output_json = _AgentReportSchema
    return task


# Simple in-memory store for short discipline summaries
_discipline_memory: dict[str, list[str]] = {}


def _memory_push(discipline: str, summary: str, max_entries: int = 5):
    """Persist a short summary for the discipline for later prompts."""
    if not summary:
        return
    _discipline_memory.setdefault(discipline, []).append(summary.strip())
    # Keep only recent entries
    _discipline_memory[discipline] = _discipline_memory[discipline][-max_entries:]


def _memory_block(discipline: str) -> str:
    entries = _discipline_memory.get(discipline, [])
    if not entries:
        return ""
    return "\nRECENT NOTES:" + "\n- " + "\n- ".join(entries)


def _log_agent_trace(discipline: str, content: dict):
    """Append agent output to a local trace file for rollback/debugging."""
    try:
        trace_path = os.path.join(os.path.dirname(__file__), "agent_traces.log")
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "discipline": discipline,
                "payload": content
            }) + "\n")
    except Exception as e:
        logger.debug(f"Trace logging skipped: {e}")


def _prioritize_items(items: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    """Sort items by risk (high first) and trim to limit."""
    if not items:
        return []
    prioritized = sorted(
        items,
        key=lambda x: (
            0 if (x.get('Days in Backlog', 0) > 90 or (x.get('SECE', False) and x.get('Days in Backlog', 0) > 60)) else 1,
            -x.get('Days in Backlog', 0),
            not x.get('SECE', False)
        )
    )
    return prioritized[:limit]


def _summarize_items_for_prompt(items: List[Dict[str, Any]], limit_fields: bool = True) -> list[dict]:
    """Keep a compact view for context hygiene."""
    compact = []
    for item in items:
        if limit_fields:
            compact.append({
                "Tag": item.get('Tag', 'N/A'),
                "Item Class": item.get('Item Class', 'N/A'),
                "Description": (item.get('Description') or '')[:80],
                "Days in Backlog": item.get('Days in Backlog', 0),
                "SECE": item.get('SECE', False),
                "Order Status": item.get('Order Status', 'N/A'),
                "Job Done": item.get('Job Done', 'N/A'),
                "Due Date": item.get('Due Date', 'N/A'),
                "System": item.get('System', 'N/A'),
                "Location": item.get('Location', 'N/A')
            })
        else:
            compact.append(item)
    return compact


def _route_disciplines_from_message(message: str) -> list[str]:
    """Heuristic routing of disciplines based on user text."""
    msg = message.lower()
    routes = []
    for name in DISCIPLINE_CATEGORIES.keys():
        if name in msg:
            routes.append(name)
    # keyword hints
    hints = {
        "psv": ["psv", "safety valve", "relief"],
        "pipeline": ["pipeline", "pig", "ili"],
        "subsea": ["subsea", "tree", "umbilical"],
        "corrosion": ["corrosion", "coating", "cp"],
        "fuims": ["fire", "gas", "shutdown", "fu"],
        "topsides": ["vessel", "piping", "tank", "structure"],
        "methods": ["procedure", "standard", "method"]
    }
    for disc, keys in hints.items():
        if any(k in msg for k in keys) and disc not in routes:
            routes.append(disc)
    return routes


def _build_cache_key(message: str, discipline: str, site: str, items_hash: str) -> str:
    """Generate cache key for query response caching"""
    raw = f"{message.lower().strip()}|{discipline}|{site}|{items_hash}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached response if available and not expired"""
    if cache_key in _RESPONSE_CACHE:
        cached_entry = _RESPONSE_CACHE[cache_key]
        age = time.time() - cached_entry["timestamp"]
        if age < _CACHE_TTL:
            logger.info(f"Cache HIT for query (age: {age:.0f}s)")
            return cached_entry["response"]
        else:
            # Expired, remove from cache
            del _RESPONSE_CACHE[cache_key]
    return None


def _cache_response(cache_key: str, response: Dict[str, Any]):
    """Cache response with timestamp"""
    _RESPONSE_CACHE[cache_key] = {
        "response": response,
        "timestamp": time.time()
    }
    logger.info(f"Cached response (total cached: {len(_RESPONSE_CACHE)})")


def _load_items_from_cache(site: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """Load latest cached raw items from SQLite cache, optionally filtered by site.

    Args:
        site: Optional site identifier (GIR, DAL, PAZ, CLV) to filter by filename prefix
    """
    try:
        cached_files = list_cached_files(site=site)
        if not cached_files:
            logger.warning(f"No cached files found for site: {site}" if site else "No cached files found")
            return None
            
        for entry in cached_files:
            # Validate site match if site is specified
            if site:
                filename_prefix = entry.get("filename", "").upper()[:3]
                if filename_prefix != site.upper():
                    logger.warning(f"Skipping {entry.get('filename')} - site mismatch (expected {site}, got {filename_prefix})")
                    continue
                    
            cached = get_cached_data(entry.get("file_hash"))
            if cached and cached.get("raw_items"):
                logger.info(f"Loaded {len(cached['raw_items'])} items from cache for site: {site or 'all'}")
                return cached["raw_items"]
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
    return None


def _parse_due_date(due_date_str: str) -> Optional[_date]:
    if not due_date_str or due_date_str == 'N/A':
        return None
    if isinstance(due_date_str, _date):
        return due_date_str
    try:
        return _dt.strptime(str(due_date_str).strip(), '%Y-%m-%d').date()
    except Exception:
        for fmt in ('%d/%m/%Y', '%m/%d/%Y'):
            try:
                return _dt.strptime(str(due_date_str).strip(), fmt).date()
            except Exception:
                continue
    return None


def _is_pending_item(item: dict, today: _date) -> bool:
    order_status = (item.get('Order Status') or '').upper().strip()
    valid_statuses = ['APPR', 'INIT', 'WREA', 'WREL']
    if order_status not in valid_statuses:
        return False
    due_date = _parse_due_date(item.get('Due Date', ''))
    if not due_date:
        return False
    return due_date + _td(days=28) > today


# Discipline-specific category mappings (based on "Item Class" field)
DISCIPLINE_CATEGORIES = {
    "topsides": [
        "Pressure Vessel (VII)",
        "Pressure Vessel (VIE)",
        "Non-Structural Tank",
        "Structures",
        "Piping",
    ],
    "fuims": [
        "FU Items",
        "Fire & Gas",
        "Emergency Shutdown",
        "Safety System",
    ],
    "psv": [
        "Pressure Safety Device",
        "PSV",
        "Safety Valve",
        "Relief Valve",
    ],
    "subsea": [
        "Subsea",
        "XMAS Tree",
        "Christmas Tree",
        "Manifold",
        "Umbilical",
    ],
    "pipeline": [
        "Intelligent Pigging",
        "ILI",
        "Pigging",
        "Pipeline Inspection",
    ],
    "corrosion": [
        "Corrosion Monitoring",
        "Corrosion",
        "Coating",
        "Cathodic Protection",
        "CP",
    ],
    "methods": [
        "Method",
        "Procedure",
        "Standard",
        "Specification",
    ],
}


def _filter_items_by_category(items: List[Dict[str, Any]], categories: List[str]) -> List[Dict[str, Any]]:
    """Filter items by Item Class category (case-insensitive partial match)"""
    filtered = []
    for item in items:
        item_class = (item.get('Item Class', '') or '').upper()
        for category in categories:
            if category.upper() in item_class:
                filtered.append(item)
                break
    return filtered


def _calculate_kpi_snapshot(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate KPI snapshot for a set of items"""
    if not items:
        return {
            "total": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "sece_count": 0,
            "overdue_count": 0,
            "backlog_count": 0,
            "pending_count": 0,
            "completed_count": 0,
            "completion_rate": 0.0
        }
    
    total = len(items)
    def _is_sece(item):
        """Derive SECE from boolean or raw SECE STATUS field."""
        if item.get('SECE', False):
            return True
        return str(item.get('SECE STATUS', '')).upper().strip() in ('SCE', 'SECE')

    high_risk = sum(1 for item in items if item.get('Days in Backlog', 0) > 90 or
                    (_is_sece(item) and item.get('Days in Backlog', 0) > 60))
    medium_risk = sum(1 for item in items if 30 < item.get('Days in Backlog', 0) <= 90)
    low_risk = total - high_risk - medium_risk
    sece_count = sum(1 for item in items if _is_sece(item))
    overdue_count = sum(1 for item in items if item.get('Days in Backlog', 0) > 0)
    backlog_count = sum(1 for item in items if str(item.get('Backlog?', '')).lower() in ('yes', 'y', 'true', '1'))
    completed_count = sum(1 for item in items 
                   if item.get('Order Status', '').upper() in ['QCAP', 'EXDO'] or
                      'compl' in (item.get('Job Done', '') or '').lower())
    
    # PENDING = Items with Order Status in [APPR, INIT, WREL, SWE] AND Backlog?="No"
    pending_count = sum(1 for item in items 
                       if item.get('Order Status', '').upper().strip() in ['APPR', 'INIT', 'WREL', 'SWE'] and
                          str(item.get('Backlog?', '')).lower().strip() not in ('yes', 'y', 'true', '1'))
    
    # Calculate completion rate (items with Order Status QCAP/EXDO)
    completion_rate = (completed_count / total * 100) if total > 0 else 0.0
    
    return {
        "total": total,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "sece_count": sece_count,
        "overdue_count": overdue_count,
        "backlog_count": backlog_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "completion_rate": round(completion_rate, 1)
    }


def _create_agent(discipline: str, role: str, goal: str, backstory: str, 
                 llm: Optional[Any] = None) -> Optional[Any]:
    """Create a CrewAI agent for a specific discipline"""
    if not AI_AVAILABLE or Agent is None:
        return None
    
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm,
        verbose=False,
        allow_delegation=False
    )


def _create_task(agent: Optional[Any], items: List[Dict[str, Any]], 
                discipline: str, kpi: Dict[str, Any]) -> Optional[Any]:
    """Create a CrewAI task for generating discipline-specific report"""
    if not AI_AVAILABLE or Task is None or agent is None:
        return None
    
    sample_items = items[:5] if len(items) > 5 else items

    task = Task(
        description=f"""
Analyze {len(items)} inspection items for {discipline} discipline and generate a **very terse** structured report.

KPI SNAPSHOT:
- Total Items: {kpi['total']}
- High Risk: {kpi['high_risk']}
- Medium Risk: {kpi['medium_risk']}
- Low Risk: {kpi['low_risk']}
- SECE Items: {kpi['sece_count']}
- Overdue: {kpi['overdue_count']}
- Backlog (Yes): {kpi['backlog_count']}
- Pending (APPR/INIT/WREL/SWE, Backlog?='No'): {kpi['pending_count']}
- Completed (QCAP/EXDO or Job Done=Compl): {kpi['completed_count']}
- Completion Rate: {kpi['completion_rate']}%

SAMPLE ITEMS (truncated):
{json.dumps(sample_items, indent=2)}
{"... (more items available)" if len(items) > 5 else ""}

REQUIREMENTS (KEEP IT SHORT):
1. "summary": **max 2 sentences**, direct and factual.
2. "key_findings": **max 3 items**, each <= 20 words.
3. "recommendations": **max 3 items**, each <= 20 words, concrete actions only.
4. "critical_items": up to 5 items (Tag ID, Risk, Days Overdue, SECE) – only if clearly supported by data.
5. "trends": 1 short sentence or "not in data" if trend evidence is missing.

STRICT CONSTRAINTS:
- Use ONLY the KPI snapshot and provided items; if a number is missing, write "not in data".
- Do NOT restate the question, do NOT explain your reasoning process.
- No generic safety slogans; every sentence must point to backlog data or KPIs.

OUTPUT FORMAT:
Return ONLY valid JSON with this structure:
{{
  "summary": "...",
  "key_findings": ["...", "..."],
  "recommendations": ["...", "..."],
  "critical_items": [
    {{"tag_id": "...", "risk": "...", "days_overdue": 0, "sece": true}}
  ],
  "trends": "..."
}}

No markdown, no explanations, just the JSON object.
""",
        expected_output="JSON object with short summary, 1-3 key_findings, 1-3 recommendations, critical_items, and a one-line trend",
        agent=agent
    )

    return _wrap_guardrail(task)


async def _run_discipline_agent(items: List[Dict[str, Any]], discipline: str, 
                                role: str, goal: str, backstory: str,
                                categories: List[str]) -> Dict[str, Any]:
    """Run a single discipline agent and return its report"""
    # Filter items by category
    filtered_items = _filter_items_by_category(items, categories)
    
    # Calculate KPI snapshot
    kpi = _calculate_kpi_snapshot(filtered_items)
    
    # Fallback report if AI is not available
    fallback_report = {
        "summary": f"Analysis of {kpi['total']} {discipline} items: {kpi['high_risk']} high-risk, backlog {kpi['backlog_count']}, pending {kpi['pending_count']}, completed {kpi['completed_count']}.",
        "key_findings": [
            f"Total {kpi['total']} items in {discipline} category",
            f"{kpi['high_risk']} items classified as high risk",
            f"Backlog items: {kpi['backlog_count']}; Pending items: {kpi['pending_count']}; Completed: {kpi['completed_count']}",
            f"{kpi['sece_count']} SECE items requiring special attention",
            f"Completion rate: {kpi['completion_rate']}%"
        ],
        "recommendations": [
            "Prioritize high-risk items for immediate inspection",
            "Review SECE items for compliance requirements",
            "Schedule overdue items as soon as possible",
            "Monitor completion rate trends"
        ],
        "critical_items": [
            {
                "tag_id": item.get('Tag', 'N/A'),
                "risk": "High" if item.get('Days in Backlog', 0) > 90 else "Medium",
                "days_overdue": item.get('Days in Backlog', 0),
                "sece": item.get('SECE', False)
            }
            for item in sorted(filtered_items, 
                             key=lambda x: (x.get('Days in Backlog', 0), x.get('SECE', False)), 
                             reverse=True)[:5]
        ],
        "trends": f"Analysis based on {kpi['total']} items with {kpi['completion_rate']}% completion rate"
    }
    
    if not AI_AVAILABLE:
        logger.info(f"AI not available, using fallback report for {discipline}")
        return {
            "discipline": discipline,
            "kpi": kpi,
            "item_count": len(filtered_items),
            "report": fallback_report,
            "ai_used": False
        }
    
    try:
        # Initialize LLM
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            logger.warning(f"OPENROUTER_API_KEY not set, using fallback for {discipline}")
            return {
                "discipline": discipline,
                "kpi": kpi,
                "item_count": len(filtered_items),
                "report": fallback_report,
                "ai_used": False
            }
        
        # Build crewai.LLM — uses LiteLLM with "openrouter/<model>" prefix so
        # LiteLLM routes correctly through OpenRouter's proxy endpoint.
        llm = _build_crewai_llm()

        # Create agent and task
        agent = _create_agent(discipline, role, goal, backstory, llm)
        task = _create_task(agent, filtered_items, discipline, kpi)
        
        if agent is None or task is None:
            return {
                "discipline": discipline,
                "kpi": kpi,
                "item_count": len(filtered_items),
                "report": fallback_report,
                "ai_used": False
            }
        
        # Execute crew (use kickoff_async in async context; CrewAI 1.x returns CrewOutput)
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=False
        )

        logger.info(f"Running {discipline} agent analysis...")
        result = await crew.kickoff_async()

        # CrewAI 1.x: result is CrewOutput — use .json_dict first, then .raw
        report = None
        if hasattr(result, 'json_dict') and result.json_dict:
            report = result.json_dict
        else:
            result_str = (result.raw if hasattr(result, 'raw') else str(result)).strip()
            # Try to extract JSON if wrapped in markdown
            if '```json' in result_str:
                result_str = result_str.split('```json')[1].split('```')[0].strip()
            elif '```' in result_str:
                result_str = result_str.split('```')[1].split('```')[0].strip()
            try:
                report = json.loads(result_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from {discipline} agent, using fallback")
                report = fallback_report

        if not _validate_report_payload(report):
            logger.warning(f"Guardrail validation failed for {discipline}, using fallback")
            report = fallback_report

        # Memory + trace
        _memory_push(discipline, report.get("summary", ""))
        _log_agent_trace(discipline, {
            "kpi": kpi,
            "item_count": len(filtered_items),
            "ai_used": True,
            "report": report
        })

        return {
            "discipline": discipline,
            "kpi": kpi,
            "item_count": len(filtered_items),
            "report": report,
            "ai_used": True
        }
        
    except Exception as e:
        logger.error(f"Error running {discipline} agent: {str(e)}", exc_info=True)
        return {
            "discipline": discipline,
            "kpi": kpi,
            "item_count": len(filtered_items),
            "report": fallback_report,
            "ai_used": False,
            "error": str(e)
        }


async def chat_with_agent(
    message: str,
    discipline: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    site: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chat with a specific engineering agent or all agents using RAG (Retrieval-Augmented Generation).
    Retrieves relevant items from the dataset based on agent's discipline and Item Class categories.
    
    Args:
        message: User's question/message
        discipline: Specific discipline to chat with (None for all agents)
        items: Full list of inspection items for RAG retrieval
        context: Optional context dictionary (site, dashboard stats, etc.)
        site: Optional site identifier (GIR, DAL, PAZ, CLV) to filter cache by filename prefix
        
    Returns:
        Dictionary with agent response and metadata
    """
    if not AI_AVAILABLE:
        return {
            "response": "AI agents are not available. Please ensure CrewAI and OpenRouter API key are configured.",
            "agent": discipline or "system",
            "ai_used": False
        }
    
    try:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            return {
                "response": "OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable.",
                "agent": discipline or "system",
                "ai_used": False
            }
        
        # Build crewai.LLM with the correct provider prefix for LiteLLM routing.
        # model_id from the catalogue already carries the prefix (e.g.
        # "openrouter/minimax/mm-m2", "deepseek/deepseek-chat").
        llm = _build_crewai_llm(model_id=model_id)

        if not items:
            items = _load_items_from_cache(site=site)
            if not items:
                site_msg = f" for {site} site" if site else ""
                return {
                    "response": f"No cached data available{site_msg}. Upload a backlog file first.",
                    "agent": discipline or "system",
                    "ai_used": False
                }

        # Auto-route if discipline not explicitly set
        routed = _route_disciplines_from_message(message) if not discipline else [discipline]
        discipline = routed[0] if routed and (not discipline or discipline == 'auto') else discipline
        
        # RAG: Filter items by discipline if specified
        relevant_items = []
        if items:
            if discipline and discipline != 'all' and discipline in DISCIPLINE_CATEGORIES:
                # Filter items by this discipline's Item Class categories
                relevant_items = _filter_items_by_category(items, DISCIPLINE_CATEGORIES[discipline])
                logger.info(f"RAG: Filtered {len(relevant_items)} items for {discipline} from {len(items)} total items")
            else:
                # For "all" agents, use all items but prioritize high-risk items
                relevant_items = items
                logger.info(f"RAG: Using all {len(relevant_items)} items for multi-agent analysis")
        
        # Calculate KPI snapshot for relevant items
        kpi = _calculate_kpi_snapshot(relevant_items) if relevant_items else {}
        
        # Determine which agent(s) to use
        if discipline and discipline != 'all':
            # Single agent response with RAG
            disc_info = None
            disc_configs = [
                {"name": "topsides", "role": "Topsides Engineer", "backstory": "You oversee topside integrity for pressure vessels (VII/VIE), non-structural tanks, structures, and piping. You blend SECE focus with production realities to burn down overdue inspections."},
                {"name": "fuims", "role": "FUIMS Engineer", "backstory": "You specialize in fire and utility instrumented systems, spotting silent failures, overdue proof tests, and missing verifications that undermine protection layers."},
                {"name": "psv", "role": "PSV Engineer", "backstory": "Pressure protection authority with a track record of clearing PSV queues, validating set pressures, and coordinating outage windows to avoid overpressure scenarios."},
                {"name": "subsea", "role": "Subsea Engineer", "backstory": "Subsea specialist experienced with trees, manifolds, and umbilicals who translates subsea findings into clear actions and campaign plans."},
                {"name": "pipeline", "role": "Pipeline Engineer", "backstory": "Pipeline integrity engineer skilled at planning and interpreting intelligent pigging, aligning anomaly responses with operations windows."},
                {"name": "corrosion", "role": "Corrosion Engineer", "backstory": "Corrosion control lead using probes, UT readings, and coatings assessments to prevent leaks and extend asset life."},
                {"name": "methods", "role": "Methods Engineer", "backstory": "Methods engineer specializing in inspection procedures, standards compliance, and quality assurance across all engineering disciplines."}
            ]
            
            for disc in disc_configs:
                if disc["name"] == discipline:
                    disc_info = disc
                    break
            
            if not disc_info:
                return {
                    "response": f"Unknown discipline: {discipline}",
                    "agent": "system",
                    "ai_used": False
                }
            
            agent = _create_agent(
                disc_info["name"],
                disc_info["role"],
                f"Answer questions about {disc_info['name']} engineering using actual inspection backlog data",
                disc_info["backstory"],
                llm
            )
            
            if agent is None:
                return {
                    "response": "Failed to create agent. Please try again.",
                    "agent": discipline,
                    "ai_used": False
                }
            
            # Build cache key for this query
            items_hash = hashlib.md5(json.dumps(relevant_items, sort_keys=True).encode()).hexdigest()[:8]
            cache_key = _build_cache_key(message, discipline, site or "", items_hash)

            # Check cache first
            cached = _get_cached_response(cache_key)
            if cached:
                logger.info(f"Returning cached response for {discipline}")
                return cached

            # Prepare RAG context with relevant items
            # Prioritize: high-risk items, overdue items, SECE items
            prioritized_items = _prioritize_items(relevant_items, limit=20)

            # Build comprehensive context string
            context_parts = []
            
            if kpi:
                context_parts.append(f"""
DATASET SUMMARY (Your Discipline - {disc_info['role']}):
- Total Items: {kpi['total']}
- High Risk: {kpi['high_risk']}
- Medium Risk: {kpi['medium_risk']}
- Low Risk: {kpi['low_risk']}
- SECE Items: {kpi['sece_count']}
- Overdue Items: {kpi['overdue_count']}
- Backlog (Yes): {kpi['backlog_count']}
- Pending (APPR/INIT/WREA/WREL within 28d): {kpi['pending_count']}
- Completed (QCAP/EXDO or Job Done=Compl): {kpi['completed_count']}
- Completion Rate: {kpi['completion_rate']}%
""")
            
            if prioritized_items:
                # Include detailed item data for RAG
                # Reduced from 15 to 5 for faster LLM processing (30-50% fewer tokens)
                items_summary = _summarize_items_for_prompt(prioritized_items[:5])
                
                context_parts.append(f"""
RELEVANT INSPECTION ITEMS (Filtered by your discipline's Item Class categories):
{json.dumps(items_summary, indent=2)}

Note: These are the items most relevant to your discipline. Use specific data from these items in your answer.
""")
            
            memory_note = _memory_block(discipline)
            if memory_note:
                context_parts.append(memory_note)
            
            if context:
                context_parts.append(f"\nAdditional Context: {json.dumps(context, indent=2)}")
            
            context_str = "\n".join(context_parts)
            extra_instruction = ""
            if discipline == 'methods':
                extra_instruction = "\n9. For Methods: summarize backlog, pending, and completed work orders using the KPI counts above."
            
            task = Task(
                description=f"""
You are a {disc_info['role']} helping with inspection backlog analysis.

USER QUESTION (answer briefly): {message}

RAG CONTEXT:
{context_str}

INSTRUCTIONS (BE TERSE):
1. Use only the provided KPIs and items; if something is missing, say "not in data".
2. Reference specific Tag IDs and numbers; avoid generic safety advice or long explanations.
3. Give **at most 3 bullet-level insights** and **at most 3 short recommendations** (one sentence each).
4. Prefer lists or tight paragraphs over narrative; no restating of the question.
5. If data is insufficient for a claim (e.g., trend or root cause), state that explicitly.
6. Do not add outside knowledge—use only the data and KPIs above.
{extra_instruction}

Answer the user's question in a concise, data-backed way.
""",
                expected_output="A short, data-driven answer (few sentences / bullets) referencing specific items from the inspection backlog",
                agent=agent
            )
            
            crew = Crew(agents=[agent], tasks=[task], verbose=False)
            result = await crew.kickoff_async()

            # CrewAI 1.x: use .raw for string output
            result_str = result.raw if hasattr(result, 'raw') else str(result)

            response_payload = {
                "response": result_str.strip(),
                "agent": discipline,
                "ai_used": True,
                "items_analyzed": len(relevant_items)
            }
            _log_agent_trace(discipline, response_payload)

            # Cache the response before returning
            _cache_response(cache_key, response_payload)

            return response_payload
        else:
            # Build cache key for "all agents" query
            items_hash = hashlib.md5(json.dumps(relevant_items, sort_keys=True).encode()).hexdigest()[:8]
            cache_key = _build_cache_key(message, "all", site or "", items_hash)

            # Check cache first
            cached = _get_cached_response(cache_key)
            if cached:
                logger.info(f"Returning cached response for all agents")
                return cached

            # All agents - create a coordinator agent with RAG from all disciplines
            coordinator = Agent(
                role="Engineering Coordinator",
                goal="Coordinate responses from multiple engineering disciplines using actual inspection backlog data",
                backstory="You coordinate insights from topsides, FUIMS, PSV, subsea, pipeline, corrosion, and methods engineers. You have access to the full inspection backlog dataset and can analyze items across all disciplines.",
                llm=llm,
                verbose=False
            )

            # For "all agents", use all items but prioritize high-risk across all disciplines
            prioritized_items = _prioritize_items(relevant_items, limit=25)
            
            # Build comprehensive context
            context_parts = []
            
            if kpi:
                context_parts.append(f"""
FULL DATASET SUMMARY (All Disciplines):
- Total Items: {kpi['total']}
- High Risk: {kpi['high_risk']}
- Medium Risk: {kpi['medium_risk']}
- Low Risk: {kpi['low_risk']}
- SECE Items: {kpi['sece_count']}
- Overdue Items: {kpi['overdue_count']}
- Backlog (Yes): {kpi['backlog_count']}
- Pending (APPR/INIT/WREA/WREL within 28d): {kpi['pending_count']}
- Completed (QCAP/EXDO or Job Done=Compl): {kpi['completed_count']}
- Completion Rate: {kpi['completion_rate']}%
""")
            
            if prioritized_items:
                # Group items by discipline for better context
                items_by_discipline = {}
                for item in prioritized_items[:20]:
                    item_class = item.get('Item Class', '').upper()
                    assigned = False
                    for disc_name, categories in DISCIPLINE_CATEGORIES.items():
                        if any(cat.upper() in item_class for cat in categories):
                            if disc_name not in items_by_discipline:
                                items_by_discipline[disc_name] = []
                            items_summary = {
                                "Tag": item.get('Tag', 'N/A'),
                                "Item Class": item.get('Item Class', 'N/A'),
                                "Description": item.get('Description', 'N/A')[:50],
                                "Days in Backlog": item.get('Days in Backlog', 0),
                                "SECE": item.get('SECE', False),
                                "Order Status": item.get('Order Status', 'N/A'),
                                "System": item.get('System', 'N/A')
                            }
                            items_by_discipline[disc_name].append(items_summary)
                            assigned = True
                            break
                    if not assigned:
                        if 'other' not in items_by_discipline:
                            items_by_discipline['other'] = []
                        items_by_discipline['other'].append({
                            "Tag": item.get('Tag', 'N/A'),
                            "Item Class": item.get('Item Class', 'N/A'),
                            "Days in Backlog": item.get('Days in Backlog', 0),
                            "SECE": item.get('SECE', False)
                        })
                
                context_parts.append(f"""
INSPECTION ITEMS BY DISCIPLINE (Top priority items):
{json.dumps(items_by_discipline, indent=2)}

Use specific data from these items when answering. Reference Tag IDs and actual metrics.
""")
            
            if context:
                context_parts.append(f"\nAdditional Context: {json.dumps(context, indent=2)}")
            
            context_str = "\n".join(context_parts)
            
            task = Task(
                description=f"""
USER QUESTION: {message}

{context_str}

INSTRUCTIONS:
1. Analyze the inspection backlog data across ALL engineering disciplines
2. Draw insights from topsides, FUIMS, PSV, subsea, pipeline, corrosion, and methods perspectives
3. Reference specific items by Tag ID when relevant
4. Use actual numbers from the dataset
5. Provide a comprehensive, well-structured answer (4-5 paragraphs)
6. Address the question from multiple engineering perspectives
7. If data is missing, say so; do not speculate or add outside knowledge.
8. Keep the answer tight and factual.

Answer the user's question using the actual inspection backlog data provided above.
""",
                expected_output="A comprehensive, data-driven answer incorporating insights from all engineering disciplines",
                agent=coordinator
            )
            
            crew = Crew(agents=[coordinator], tasks=[task], verbose=False)
            result = await crew.kickoff_async()

            # CrewAI 1.x: use .raw for string output
            result_str = result.raw if hasattr(result, 'raw') else str(result)

            response_payload = {
                "response": result_str.strip(),
                "agent": "all",
                "ai_used": True,
                "items_analyzed": len(relevant_items) if relevant_items else 0
            }
            _log_agent_trace("all", response_payload)

            # Cache the response before returning
            _cache_response(cache_key, response_payload)

            return response_payload
            
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return {
            "response": f"I encountered an error: {str(e)}. Please try rephrasing your question.",
            "agent": discipline or "system",
            "ai_used": False,
            "error": str(e)
        }


async def run_engineering_agents(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run multi-agent engineering analysis on inspection items.
    
    Args:
        items: List of inspection items from Excel "Data Base" sheet
        
    Returns:
        Dictionary containing reports from all discipline agents
    """
    # Note: run_engineering_agents doesn't currently receive site parameter
    # It will load the most recent cache regardless of site
    # This is acceptable for the agentic report endpoint which processes all items
    if not items:
        items = _load_items_from_cache() or []
    if not items:
        return {
            "success": False,
            "message": "No cached backlog data available. Upload a file first.",
            "reports": {}
        }
    logger.info(f"Starting multi-agent engineering analysis for {len(items)} items")
    
    # Define discipline agents
    disciplines = [
        {
            "name": "topsides",
            "role": "Topsides Engineer",
            "goal": "Analyze topside static equipment backlog (pressure vessels VII/VIE, non-structural tanks, structures, piping) and identify critical items requiring immediate attention",
            "backstory": "You oversee topside integrity for pressure vessels, tanks, structures, and piping. You blend SECE focus with production realities to burn down overdue inspections.",
            "categories": DISCIPLINE_CATEGORIES["topsides"]
        },
        {
            "name": "fuims",
            "role": "FUIMS Engineer",
            "goal": "Evaluate fire, utility, instrumented, and monitoring systems backlog with emphasis on FU items and shutdown readiness",
            "backstory": "You specialize in fire and utility instrumented systems, spotting silent failures, overdue proof tests, and missing verifications that undermine protection layers.",
            "categories": DISCIPLINE_CATEGORIES["fuims"]
        },
        {
            "name": "psv",
            "role": "PSV Engineer",
            "goal": "Assess pressure safety device backlog and spotlight overdue critical protection points",
            "backstory": "Pressure protection authority with a track record of clearing PSV queues, validating set pressures, and coordinating outage windows to avoid overpressure scenarios.",
            "categories": DISCIPLINE_CATEGORIES["psv"]
        },
        {
            "name": "subsea",
            "role": "Subsea Engineer",
            "goal": "Analyze subsea integrity backlog focusing on xmas trees, manifolds, and control infrastructure",
            "backstory": "Subsea specialist experienced with trees, manifolds, and umbilicals who translates subsea findings into clear actions and campaign plans.",
            "categories": DISCIPLINE_CATEGORIES["subsea"]
        },
        {
            "name": "pipeline",
            "role": "Pipeline / Intelligent Pigging Engineer",
            "goal": "Evaluate intelligent pigging and pipeline inspection backlog to keep ILI campaigns on track",
            "backstory": "Pipeline integrity engineer skilled at planning and interpreting intelligent pigging, aligning anomaly responses with operations windows.",
            "categories": DISCIPLINE_CATEGORIES["pipeline"]
        },
        {
            "name": "corrosion",
            "role": "Corrosion Engineer",
            "goal": "Analyze corrosion monitoring and materials degradation backlog across all systems",
            "backstory": "Corrosion control lead using probes, UT readings, and coatings assessments to prevent leaks and extend asset life.",
            "categories": DISCIPLINE_CATEGORIES["corrosion"]
        },
        {
            "name": "methods",
            "role": "Methods & Procedures Engineer",
            "goal": "Review inspection methods, procedures, and standards compliance across all disciplines",
            "backstory": "You are a methods engineer specializing in inspection procedures, standards compliance, and quality assurance. You ensure all inspection activities follow industry best practices and regulatory requirements.",
            "categories": DISCIPLINE_CATEGORIES["methods"]
        }
    ]
    
    # Run all discipline agents
    reports = {}
    for disc in disciplines:
        logger.info(f"Processing {disc['name']} discipline...")
        report = await _run_discipline_agent(
            items, 
            disc['name'],
            disc['role'],
            disc['goal'],
            disc['backstory'],
            disc['categories']
        )
        reports[disc['name']] = report
    
    # Calculate overall summary
    total_items = len(items)
    total_ai_used = sum(1 for r in reports.values() if r.get('ai_used', False))

    return {
        "timestamp": datetime.now().isoformat(),
        "total_items": total_items,
        "disciplines_analyzed": len(reports),
        "ai_enabled": AI_AVAILABLE and bool(os.getenv("OPENROUTER_API_KEY")),
        "ai_used_count": total_ai_used,
        "reports": reports
    }


# ---------------------------------------------------------------------------
# Public A2A-facing helpers
# ---------------------------------------------------------------------------

async def run_single_discipline_agent(
    discipline: str,
    items: List[Dict[str, Any]],
    user_query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Public single-discipline entry-point used by the A2A orchestrator.

    Returns the same dict shape as _run_discipline_agent() so callers
    can treat parallel and sequential results identically.
    """
    disc_map = {
        "topsides": {
            "role": "Topsides Engineer",
            "goal": "Analyse topside static equipment backlog and identify critical items",
            "backstory": "You oversee topside integrity for pressure vessels, tanks, structures, and piping.",
        },
        "fuims": {
            "role": "FUIMS Engineer",
            "goal": "Evaluate fire, utility, instrumented, and monitoring systems backlog",
            "backstory": "You specialize in fire and utility instrumented systems.",
        },
        "psv": {
            "role": "PSV Engineer",
            "goal": "Assess pressure safety device backlog",
            "backstory": "Pressure protection authority with a track record of clearing PSV queues.",
        },
        "subsea": {
            "role": "Subsea Engineer",
            "goal": "Analyse subsea integrity backlog",
            "backstory": "Subsea specialist experienced with trees, manifolds, and umbilicals.",
        },
        "pipeline": {
            "role": "Pipeline / ILI Engineer",
            "goal": "Evaluate intelligent pigging and pipeline inspection backlog",
            "backstory": "Pipeline integrity engineer skilled at planning ILI campaigns.",
        },
        "corrosion": {
            "role": "Corrosion Engineer",
            "goal": "Analyse corrosion monitoring and materials degradation backlog",
            "backstory": "Corrosion control lead using probes, UT readings, and coatings assessments.",
        },
        "methods": {
            "role": "Methods & Procedures Engineer",
            "goal": "Review inspection methods, procedures, and standards compliance",
            "backstory": "Methods engineer specialising in inspection procedures and standards compliance.",
        },
    }

    if discipline not in disc_map:
        return {
            "discipline": discipline,
            "error": f"Unknown discipline: {discipline}",
            "kpi": {},
            "item_count": 0,
            "report": {},
            "ai_used": False,
        }

    cfg = disc_map[discipline]
    categories = DISCIPLINE_CATEGORIES.get(discipline, [])
    return await _run_discipline_agent(
        items,
        discipline,
        cfg["role"],
        cfg["goal"],
        cfg["backstory"],
        categories,
    )


async def run_engineering_agents_parallel(
    items: List[Dict[str, Any]],
    disciplines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Drop-in replacement for run_engineering_agents() that executes all
    discipline agents CONCURRENTLY via asyncio.gather().

    Reduces wall-clock time from O(n × agent_latency) to O(max agent_latency).
    """
    if not items:
        items = _load_items_from_cache() or []
    if not items:
        return {
            "success": False,
            "message": "No cached backlog data available. Upload a file first.",
            "reports": {}
        }

    target = disciplines or list(DISCIPLINE_CATEGORIES.keys())
    logger.info(f"Parallel execution: {len(target)} discipline agents")

    coros = [run_single_discipline_agent(disc, items) for disc in target]
    results_list: List[Dict[str, Any]] = await asyncio.gather(*coros)

    reports = {r["discipline"]: r for r in results_list}
    total_ai_used = sum(1 for r in reports.values() if r.get("ai_used", False))

    return {
        "timestamp": datetime.now().isoformat(),
        "total_items": len(items),
        "disciplines_analyzed": len(reports),
        "ai_enabled": AI_AVAILABLE and bool(os.getenv("OPENROUTER_API_KEY")),
        "ai_used_count": total_ai_used,
        "parallel": True,
        "reports": reports,
    }
