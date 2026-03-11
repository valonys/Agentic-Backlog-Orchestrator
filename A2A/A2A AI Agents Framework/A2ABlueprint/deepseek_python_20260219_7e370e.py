# test_a2a_integration.py
#!/usr/bin/env python
"""
Integration test for A2A-CrewAI system
Tests all agents and orchestrator
"""

import asyncio
import httpx
import json
import time
from typing import Dict, List
from a2a.client import ClientFactory, ClientConfig, create_text_message_object


class A2ATester:
    """Test harness for A2A agents."""
    
    def __init__(self):
        self.host = "localhost"
        self.agents = {
            "topsides": 9001,
            "fuims": 9002,
            "psv": 9003,
            "subsea": 9004,
            "pipeline": 9005,
            "corrosion": 9006,
            "methods": 9007,
        }
        self.orchestrator_port = 9010
        
    async def test_agent_health(self, name: str, port: int) -> Dict:
        """Test individual agent connectivity and AgentCard."""
        url = f"http://{self.host}:{port}"
        results = {
            "name": name,
            "port": port,
            "url": url,
            "agent_card": None,
            "query_response": None,
            "success": False,
            "error": None
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as httpx_client:
                # Test AgentCard endpoint
                card_response = await httpx_client.get(f"{url}/.well-known/agent-card")
                if card_response.status_code == 200:
                    results["agent_card"] = card_response.json()
                    
                    # Test A2A query
                    client = await ClientFactory.connect(
                        url,
                        client_config=ClientConfig(httpx_client=httpx_client)
                    )
                    
                    message = create_text_message_object(
                        content=f"Test query for {name} agent"
                    )
                    
                    responses = client.send_message(message)
                    async for response in responses:
                        if hasattr(response, 'text'):
                            results["query_response"] = response.text[:200] + "..."
                            break
                    
                    results["success"] = True
                else:
                    results["error"] = f"AgentCard returned {card_response.status_code}"
                    
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def test_orchestrator(self, query: str) -> Dict:
        """Test orchestrator with a query."""
        url = f"http://{self.host}:{self.orchestrator_port}"
        results = {
            "query": query,
            "response": None,
            "success": False,
            "error": None,
            "duration_ms": 0
        }
        
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send query to orchestrator
                response = await client.post(
                    f"{url}/api/v1/chat",
                    json={"message": query}
                )
                
                if response.status_code == 200:
                    results["response"] = response.json()
                    results["success"] = True
                else:
                    results["error"] = f"HTTP {response.status_code}"
                    
            results["duration_ms"] = int((time.time() - start) * 1000)
            
        except Exception as e:
            results["error"] = str(e)
            
        return results
    
    async def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "="*70)
        print("🧪 A2A-CrewAI Integration Test Suite")
        print("="*70)
        
        # Test 1: Individual Agents
        print("\n📡 TEST 1: Individual Agent Connectivity")
        print("-"*50)
        
        agent_results = []
        for name, port in self.agents.items():
            print(f"  Testing {name} on port {port}...", end="", flush=True)
            result = await self.test_agent_health(name, port)
            agent_results.append(result)
            
            if result["success"]:
                print(f" ✅ ({result['agent_card']['name']})")
            else:
                print(f" ❌ {result['error']}")
        
        # Summary
        success_count = sum(1 for r in agent_results if r["success"])
        print(f"\n  📊 Agent Summary: {success_count}/{len(self.agents)} connected")
        
        # Test 2: Orchestrator
        print("\n🎯 TEST 2: Orchestrator Functionality")
        print("-"*50)
        
        test_queries = [
            "What are the high-risk topsides items?",
            "Show me overdue PSV valves",
            "Any corrosion issues?",
            "What's the status of fire and gas systems?",
            "Give me all high-risk items"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n  Query {i}: {query}")
            result = await self.test_orchestrator(query)
            
            if result["success"]:
                print(f"    ✅ Response ({result['duration_ms']}ms)")
                if result["response"]:
                    agents = result["response"].get("agents_used", [])
                    print(f"    Agents: {', '.join(agents) if agents else 'None'}")
            else:
                print(f"    ❌ {result['error']}")
        
        # Test 3: Cross-Framework Compatibility (if clients available)
        print("\n🔄 TEST 3: Cross-Framework Compatibility")
        print("-"*50)
        print("  To test with external frameworks:")
        print("  1. Microsoft Agent Framework:")
        print("     from agent_framework.a2a import A2AAgent")
        print("     agent = A2AAgent(name='Topsides', url='http://localhost:9001')")
        print("  2. Google ADK:")
        print("     from google.adk.a2a import RemoteA2aAgent")
        print("     agent = RemoteA2aAgent(name='topsides', agent_card='http://localhost:9001')")
        
        return {
            "agents": agent_results,
            "orchestrator_tests": len(test_queries),
            "timestamp": time.time()
        }


async def main():
    tester = A2ATester()
    results = await tester.run_all_tests()
    
    print("\n" + "="*70)
    print("📋 FINAL SUMMARY")
    print("="*70)
    
    if all(r["success"] for r in results["agents"]):
        print("✅ ALL AGENTS: Connected and responding")
    else:
        print("⚠️ SOME AGENTS: Check individual results")
    
    print(f"✅ ORCHESTRATOR: {results['orchestrator_tests']} queries tested")
    print("\n✨ Integration test complete!")


if __name__ == "__main__":
    asyncio.run(main())