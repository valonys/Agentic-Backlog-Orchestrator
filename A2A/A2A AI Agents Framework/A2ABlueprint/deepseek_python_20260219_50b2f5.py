# a2a_backlog_orchestrator.py
#!/usr/bin/env python
"""
A2A Orchestrator using BeeAI RequirementAgent
Routes queries to appropriate discipline agents
"""

import os
import asyncio
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.agents.requirement.requirements.conditional import ConditionalRequirement
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.tools.think import ThinkTool
from beeai_framework.adapters.vertexai import VertexAIChatModel

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import authenticate
from routing_models import parse_query_intent, QueryIntent


class BacklogOrchestrator:
    """
    Orchestrator that routes queries to appropriate A2A discipline agents.
    """
    
    def __init__(self):
        load_dotenv()
        self.host = os.environ.get("AGENT_HOST", "localhost")
        self.discipline_agents = {}
        self.orchestrator = None
        
        # Port mapping
        self.ports = {
            "topsides": os.environ.get("TOPSIDES_AGENT_PORT", 9001),
            "fuims": os.environ.get("FUIMS_AGENT_PORT", 9002),
            "psv": os.environ.get("PSV_AGENT_PORT", 9003),
            "subsea": os.environ.get("SUBSEA_AGENT_PORT", 9004),
            "pipeline": os.environ.get("PIPELINE_AGENT_PORT", 9005),
            "corrosion": os.environ.get("CORROSION_AGENT_PORT", 9006),
            "methods": os.environ.get("METHODS_AGENT_PORT", 9007),
        }
        
    async def initialize(self):
        """Initialize connections to all discipline A2A agents."""
        print("\n🔌 Connecting to discipline agents...")
        
        for discipline, port in self.ports.items():
            try:
                agent = A2AAgent(
                    url=f"http://{self.host}:{port}",
                    memory=UnconstrainedMemory()
                )
                await agent.check_agent_exists()
                self.discipline_agents[discipline] = agent
                print(f"  ✅ {discipline} - {agent.agent_card.name}")
            except Exception as e:
                print(f"  ❌ {discipline} - Connection failed: {e}")
        
        print(f"\n📊 Connected to {len(self.discipline_agents)} agents")
        
        # Create orchestrator
        await self._create_orchestrator()
    
    async def _create_orchestrator(self):
        """Create the BeeAI RequirementAgent with handoff tools."""
        print("\n🤖 Creating orchestrator agent...")
        
        # Authenticate to Vertex AI
        credentials, project_id = authenticate()
        
        # Create handoff tools for each discipline
        handoff_tools = []
        for discipline, agent in self.discipline_agents.items():
            handoff_tools.append(
                HandoffTool(
                    target=agent,
                    name=agent.name,
                    description=agent.agent_card.description,
                )
            )
        
        # Add think tool for reasoning
        think_tool = ThinkTool()
        
        # Build agent description
        agent_descriptions = "\n".join([
            f"  - {d}: {a.agent_card.description[:100]}..."
            for d, a in self.discipline_agents.items()
        ])
        
        # Create orchestrator
        self.orchestrator = RequirementAgent(
            name="BacklogOrchestrator",
            description="Routes backlog queries to appropriate discipline engineers",
            llm=VertexAIChatModel(
                model_id="gemini-2.5-flash",
                project=project_id,
                location="global",
                allow_parallel_tool_calls=True,
            ),
            tools=[think_tool] + handoff_tools,
            requirements=[
                ConditionalRequirement(
                    think_tool, 
                    force_at_step=1,  # Think first
                    consecutive_allowed=False
                ),
            ],
            role="Backlog Analysis Coordinator",
            instructions=f"""
            You are a coordinator for offshore inspection backlog analysis.
            
            Your task:
            1. Analyze the user's query to determine which discipline(s) are needed
            2. Use the ThinkTool to plan which agents to call
            3. Hand off to the appropriate discipline agents using HandoffTool
            4. Synthesize their responses into a comprehensive answer
            
            Available discipline agents:
            {agent_descriptions}
            
            IMPORTANT: 
            - Call multiple agents if the query spans multiple disciplines
            - Always think before acting
            - Synthesize responses from all called agents
            - If unsure which agent to call, think first then decide
            """,
        )
        
        print(f"  ✅ Orchestrator created: {self.orchestrator.meta.name}")
    
    async def route_query(self, query: str, session_id: Optional[str] = None) -> Dict:
        """
        Route a query to appropriate agents and return synthesized response.
        
        Returns:
            Dict with response, agents_used, session_id
        """
        if not self.orchestrator:
            await self.initialize()
        
        # Optional: Use existing intent parser
        intent = parse_query_intent(query) if 'parse_query_intent' in dir() else None
        
        print(f"\n📨 Processing query: {query[:50]}...")
        
        # Run orchestrator
        try:
            response = await self.orchestrator.run(query)
            
            result = {
                "response": response.last_message.text,
                "agents_used": list(self.discipline_agents.keys()),  # Simplified
                "session_id": session_id or f"session-{asyncio.get_event_loop().time()}",
                "timestamp": asyncio.get_event_loop().time(),
                "success": True
            }
            
            print(f"✅ Response generated ({len(result['response'])} chars)")
            return result
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "response": f"Error processing query: {str(e)}",
                "agents_used": [],
                "session_id": session_id,
                "timestamp": asyncio.get_event_loop().time(),
                "success": False
            }
    
    async def get_agent_status(self) -> Dict:
        """Get status of all connected agents."""
        status = {}
        for name, agent in self.discipline_agents.items():
            status[name] = {
                "connected": True,
                "name": agent.name,
                "url": agent.url,
                "skills": [s.name for s in agent.agent_card.skills] if agent.agent_card else []
            }
        return {
            "orchestrator": "initialized" if self.orchestrator else "pending",
            "agents": status,
            "agent_count": len(status)
        }


# Standalone test
async def main():
    """Test the orchestrator."""
    orch = BacklogOrchestrator()
    await orch.initialize()
    
    test_queries = [
        "What are the high-risk topsides items?",
        "Show me overdue PSV valves and any corrosion issues",
        "Give me an overview of all high-risk items across all disciplines"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"🔍 QUERY: {query}")
        print(f"{'='*60}")
        
        result = await orch.route_query(query)
        print(f"\n📋 RESPONSE:\n{result['response'][:500]}...")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    asyncio.run(main())