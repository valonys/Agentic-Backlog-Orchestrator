# a2a_crew_wrapper.py
import os
import json
import asyncio
import uvicorn
from typing import List, Dict, Any, Optional

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.utils import new_agent_text_message

# Import your existing CrewAI components
from engineering_agents import run_single_discipline_agent
from models import BacklogItem
from database import get_cached_items


class CrewAIAgentExecutor(AgentExecutor):
    """
    Bridges A2A protocol to a specific CrewAI discipline agent.
    """
    def __init__(
        self, 
        discipline: str,
        role: str,
        goal: str,
        backstory: str,
        categories: List[str],
        file_hash: Optional[str] = None
    ):
        self.discipline = discipline
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.categories = categories
        self.file_hash = file_hash
        
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the CrewAI agent with the user's query."""
        # 1. Get user input
        prompt = context.get_user_input()
        
        # 2. Load relevant items
        items = await self._load_items(context)
        
        # 3. Filter items by discipline
        discipline_items = [
            item for item in items 
            if item.get("Item Class") in self.categories
        ]
        
        # 4. Run CrewAI agent
        try:
            result = await run_single_discipline_agent(
                items=discipline_items,
                discipline=self.discipline,
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                categories=self.categories,
                user_query=prompt
            )
            
            response_text = self._format_response(result, prompt)
        except Exception as e:
            response_text = f"Error: {str(e)}"
        
        # 5. Send response
        message = new_agent_text_message(response_text)
        await event_queue.enqueue_event(message)
    
    async def _load_items(self, context: RequestContext) -> List[Dict]:
        """Load items from cache or context."""
        if context.data and "items" in context.data:
            return context.data["items"]
        if self.file_hash:
            cached = get_cached_items(self.file_hash)
            if cached:
                return cached
        return []
    
    def _format_response(self, result: Dict, query: str) -> str:
        """Format CrewAI output for A2A response."""
        parts = []
        
        # Add response header
        parts.append(f"## {self.discipline.title()} Engineering Analysis")
        parts.append(f"*In response to: {query}*\n")
        
        # Add summary
        if result.get("summary"):
            parts.append(result["summary"])
        
        # Add key findings
        if result.get("key_findings"):
            parts.append("\n### Key Findings")
            for finding in result["key_findings"][:3]:
                parts.append(f"• {finding}")
        
        # Add recommendations
        if result.get("recommendations"):
            parts.append("\n### Recommendations")
            for rec in result["recommendations"][:3]:
                parts.append(f"• {rec}")
        
        # Add critical items
        if result.get("critical_items"):
            parts.append("\n### Critical Items")
            for item in result["critical_items"][:5]:
                parts.append(
                    f"• {item.get('tag_id')} - Risk: {item.get('risk')} "
                    f"(Days overdue: {item.get('days_overdue')})"
                )
        
        return "\n".join(parts)
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def create_crew_a2a_server(
    discipline: str,
    role: str,
    goal: str,
    backstory: str,
    categories: List[str],
    port: int,
    host: str = "localhost",
    file_hash: Optional[str] = None
) -> A2AStarletteApplication:
    """Factory function to create A2A server for a CrewAI agent."""
    
    executor = CrewAIAgentExecutor(
        discipline=discipline,
        role=role,
        goal=goal,
        backstory=backstory,
        categories=categories,
        file_hash=file_hash
    )
    
    skill = AgentSkill(
        id=f"{discipline}_analysis",
        name=f"{discipline.title()} Engineering Analysis",
        description=f"Analyzes {discipline} equipment and provides engineering recommendations",
        tags=["backlog", discipline, "engineering"],
        examples=[
            f"What are the high-risk {discipline} items?",
            f"Show me overdue {discipline} inspections",
        ],
    )
    
    agent_card = AgentCard(
        name=f"{discipline.title()}EngineerAgent",
        description=f"AI-powered {discipline} engineering analyst for inspection backlog",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )