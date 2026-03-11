"""
a2a_protocol.py
================
A2A (Agent-to-Agent) protocol definitions for the Backlog Orchestrator.

Implements Google's A2A protocol message contract natively — no external
a2a-sdk required.  All agent communication flows through this module:

  • AgentCard     — discovery / capability advertisement per discipline
  • A2AMessage    — JSON-RPC 2.0 task/send envelope
  • A2AResponse   — structured agent reply
  • AgentMessageBus — in-process async pub/sub for cross-discipline findings
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1.  AgentCard definitions  (A2A discovery contract)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentSkill:
    id: str
    name: str
    description: str
    tags: List[str]
    examples: List[str]


@dataclass(frozen=True)
class AgentCapabilities:
    streaming: bool = False
    parallel_execution: bool = True
    cross_agent_messaging: bool = True


@dataclass(frozen=True)
class AgentCard:
    name: str
    description: str
    discipline: str
    port: int                           # logical port (used in docker / future microservice)
    version: str
    capabilities: AgentCapabilities
    skills: List[AgentSkill]
    categories: List[str]               # Item Class values this agent handles

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "discipline": self.discipline,
            "url": self.url,
            "version": self.version,
            "capabilities": {
                "streaming": self.capabilities.streaming,
                "parallel_execution": self.capabilities.parallel_execution,
                "cross_agent_messaging": self.capabilities.cross_agent_messaging,
            },
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                    "examples": s.examples,
                }
                for s in self.skills
            ],
            "categories": self.categories,
        }


# ---------------------------------------------------------------------------
# 2.  Agent registry — one card per discipline
# ---------------------------------------------------------------------------

AGENT_CARDS: Dict[str, AgentCard] = {

    "topsides": AgentCard(
        name="TopsidesEngineerAgent",
        description=(
            "Analyzes topsides static equipment: pressure vessels (VII/VIE), "
            "non-structural tanks, structures, and piping. Prioritises SECE items "
            "and overdue inspections with production-impact context."
        ),
        discipline="topsides",
        port=9001,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="topsides_backlog_analysis",
                name="Topsides Backlog Analysis",
                description="Risk-ranked topsides backlog with SECE escalation",
                tags=["topsides", "pressure-vessel", "piping", "structures", "SECE"],
                examples=[
                    "What are the high-risk topsides items?",
                    "Show overdue pressure vessels",
                    "Which SECE topsides items need immediate escalation?",
                ],
            )
        ],
        categories=[
            "Pressure Vessel (VII)",
            "Pressure Vessel (VIE)",
            "Non-Structural Tank",
            "Structures",
            "Piping",
        ],
    ),

    "fuims": AgentCard(
        name="FUIMSEngineerAgent",
        description=(
            "Floating Unit Integrity Management System (FUIMS) engineer. "
            "Covers fire, utility, and instrumented monitoring systems. "
            "Detects silent failures, overdue proof tests, and protection-layer gaps."
        ),
        discipline="fuims",
        port=9002,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="fuims_analysis",
                name="FUIMS Analysis",
                description="Fire & gas, ESD, and safety system backlog review",
                tags=["fire-gas", "ESD", "safety-system", "FUIMS", "SECE"],
                examples=[
                    "What fire & gas items are overdue?",
                    "Are there any ESD proof test overruns?",
                ],
            )
        ],
        categories=["FU Items", "Fire & Gas", "Emergency Shutdown", "Safety System"],
    ),

    "psv": AgentCard(
        name="PSVEngineerAgent",
        description=(
            "Pressure safety valve authority — clears PSV queues, validates set "
            "pressures, and flags overpressure risk from overdue devices."
        ),
        discipline="psv",
        port=9003,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="psv_analysis",
                name="PSV Backlog Analysis",
                description="PSV and relief-valve overdue inspection review",
                tags=["PSV", "relief-valve", "overpressure", "SECE"],
                examples=[
                    "Show overdue PSV valves",
                    "Which relief valves need immediate attention?",
                ],
            )
        ],
        categories=["Pressure Safety Device", "PSV", "Safety Valve", "Relief Valve"],
    ),

    "subsea": AgentCard(
        name="SubseaEngineerAgent",
        description=(
            "Subsea integrity specialist for trees, manifolds, and umbilicals. "
            "Translates findings into campaign-ready action plans."
        ),
        discipline="subsea",
        port=9004,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="subsea_analysis",
                name="Subsea Backlog Analysis",
                description="Subsea equipment backlog and campaign planning",
                tags=["subsea", "christmas-tree", "manifold", "umbilical"],
                examples=[
                    "Any overdue subsea inspections?",
                    "Show XMAS tree backlog items",
                ],
            )
        ],
        categories=["Subsea", "XMAS Tree", "Christmas Tree", "Manifold", "Umbilical"],
    ),

    "pipeline": AgentCard(
        name="PipelineEngineerAgent",
        description=(
            "Pipeline integrity engineer for intelligent pigging and ILI campaigns. "
            "Aligns anomaly response windows with operational constraints."
        ),
        discipline="pipeline",
        port=9005,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="pipeline_analysis",
                name="Pipeline / ILI Analysis",
                description="ILI campaign status and pipeline inspection backlog",
                tags=["pipeline", "ILI", "pigging", "integrity"],
                examples=[
                    "What pipelines are overdue for ILI?",
                    "Show intelligent pigging backlog",
                ],
            )
        ],
        categories=["Intelligent Pigging", "ILI", "Pigging", "Pipeline Inspection"],
    ),

    "corrosion": AgentCard(
        name="CorrosionEngineerAgent",
        description=(
            "Corrosion control lead using UT readings, coatings assessments, and "
            "CP data to prevent leaks and extend asset life."
        ),
        discipline="corrosion",
        port=9006,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="corrosion_analysis",
                name="Corrosion Monitoring Analysis",
                description="Corrosion, coating, and cathodic protection backlog",
                tags=["corrosion", "coating", "CP", "UT", "integrity"],
                examples=[
                    "What corrosion monitoring items are overdue?",
                    "Any cathodic protection issues?",
                ],
            )
        ],
        categories=[
            "Corrosion Monitoring", "Corrosion", "Coating",
            "Cathodic Protection", "CP",
        ],
    ),

    "methods": AgentCard(
        name="MethodsEngineerAgent",
        description=(
            "Methods & procedures engineer ensuring inspection activities follow "
            "industry standards and regulatory requirements across all disciplines."
        ),
        discipline="methods",
        port=9007,
        version="1.0.0",
        capabilities=AgentCapabilities(),
        skills=[
            AgentSkill(
                id="methods_analysis",
                name="Methods & Procedures Analysis",
                description="Procedure compliance, backlog, and pending work orders",
                tags=["methods", "procedure", "standard", "compliance"],
                examples=[
                    "Are there overdue procedure reviews?",
                    "What standards need updating?",
                ],
            )
        ],
        categories=["Method", "Procedure", "Standard", "Specification"],
    ),

    "orchestrator": AgentCard(
        name="BacklogMasterOrchestratorAgent",
        description=(
            "Master orchestrator that routes queries to discipline agents in parallel, "
            "correlates cross-discipline findings, and synthesises executive reports."
        ),
        discipline="orchestrator",
        port=9010,
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False, parallel_execution=True, cross_agent_messaging=True),
        skills=[
            AgentSkill(
                id="orchestrate",
                name="Multi-Discipline Orchestration",
                description="Parallel routing + cross-discipline risk synthesis",
                tags=["orchestrator", "multi-agent", "A2A", "synthesis"],
                examples=[
                    "Give me all high-risk items across all disciplines",
                    "What cross-discipline risks need escalation?",
                ],
            )
        ],
        categories=[],   # handles all
    ),
}


# ---------------------------------------------------------------------------
# 3.  A2A JSON-RPC 2.0 message models
# ---------------------------------------------------------------------------

class A2AMessagePart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class A2AMessage(BaseModel):
    """Inbound task/send envelope (Google A2A JSON-RPC 2.0)."""
    jsonrpc: str = "2.0"
    method: Literal["tasks/send"] = "tasks/send"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    params: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(cls, text: str, task_id: Optional[str] = None) -> "A2AMessage":
        return cls(
            params={
                "id": task_id or str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": text}],
                },
            }
        )

    @property
    def user_text(self) -> str:
        parts = self.params.get("message", {}).get("parts", [])
        return " ".join(p.get("text", "") for p in parts if p.get("type") == "text")


class A2AResponse(BaseModel):
    """Agent reply envelope."""
    task_id: str
    agent: str
    discipline: str
    status: Literal["completed", "failed", "no_data"]
    text: str
    kpi: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    cross_discipline_findings: List[Dict[str, Any]] = Field(default_factory=list)
    ai_used: bool = False
    duration_ms: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class OrchestratorReport(BaseModel):
    """Final synthesised output from the master orchestrator."""
    session_id: str
    query: str
    disciplines_invoked: List[str]
    parallel_execution: bool = True
    total_duration_ms: int = 0
    cross_discipline_risks: List[Dict[str, Any]] = Field(default_factory=list)
    executive_summary: str = ""
    agent_responses: Dict[str, A2AResponse] = Field(default_factory=dict)
    routing_mode: Literal["single", "multi", "all"] = "multi"
    ai_used: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ---------------------------------------------------------------------------
# 4.  AgentMessageBus — in-process async pub/sub for cross-agent findings
# ---------------------------------------------------------------------------

class AgentMessageBus:
    """
    Lightweight async pub/sub bus scoped to a single orchestration session.

    Discipline agents publish findings after completing their analysis.
    The orchestrator (and other agents) can subscribe to receive those
    findings before synthesising the final report — enabling genuine
    agent-to-agent communication without an external message broker.

    Usage
    -----
    bus = AgentMessageBus(session_id="abc123")

    # In discipline agent after analysis:
    await bus.publish("corrosion", {
        "type": "cross_discipline_finding",
        "target": "psv",          # PSV agent should know about this
        "tag_id": "GIR-PSV-042",
        "finding": "Active corrosion detected on PSV body",
        "severity": "High",
    })

    # In orchestrator after gathering all agents:
    findings = bus.drain()        # returns all published messages
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._published: List[Dict[str, Any]] = []

    async def publish(self, source_discipline: str, message: Dict[str, Any]) -> None:
        """Publish a finding from a discipline agent."""
        envelope = {
            "session_id": self.session_id,
            "source": source_discipline,
            "timestamp": datetime.utcnow().isoformat(),
            **message,
        }
        self._published.append(envelope)
        await self._queue.put(envelope)

    def drain(self) -> List[Dict[str, Any]]:
        """Return all published messages (non-blocking snapshot)."""
        return list(self._published)

    def cross_discipline_findings_for(self, discipline: str) -> List[Dict[str, Any]]:
        """Return messages that target a specific discipline."""
        return [
            m for m in self._published
            if m.get("target") == discipline or m.get("target") == "all"
        ]

    def high_severity_findings(self) -> List[Dict[str, Any]]:
        """Return all High-severity cross-discipline findings."""
        return [m for m in self._published if m.get("severity") == "High"]


# ---------------------------------------------------------------------------
# 5.  Session registry (module-level, lives for the process lifetime)
# ---------------------------------------------------------------------------

_active_buses: Dict[str, AgentMessageBus] = {}


def get_or_create_bus(session_id: str) -> AgentMessageBus:
    """Get an existing bus or create one for this session."""
    if session_id not in _active_buses:
        _active_buses[session_id] = AgentMessageBus(session_id)
    return _active_buses[session_id]


def release_bus(session_id: str) -> None:
    """Release a bus after orchestration completes."""
    _active_buses.pop(session_id, None)
