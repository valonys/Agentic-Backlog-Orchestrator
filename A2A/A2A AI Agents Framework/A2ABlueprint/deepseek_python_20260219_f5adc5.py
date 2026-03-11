# a2a_topsides_agent.py
#!/usr/bin/env python
"""
A2A-compliant Topsides Engineering Agent
Runs as independent server on port 9001
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_crew_wrapper import create_crew_a2a_server
from engineering_agents import DISCIPLINE_CATEGORIES

# Load environment
load_dotenv()

# Configuration
HOST = os.environ.get("AGENT_HOST", "localhost")
PORT = int(os.environ.get("TOPSIDES_AGENT_PORT", 9001))
FILE_HASH = os.environ.get("CURRENT_FILE_HASH")  # Optional cached data

AGENT_CONFIG = {
    "discipline": "topsides",
    "role": "Topsides Engineer",
    "goal": "Analyze topsides equipment including pressure vessels, structures, and piping",
    "backstory": (
        "You are a senior topsides engineer with 20 years of offshore experience. "
        "You specialize in pressure vessels, structural integrity, and piping systems. "
        "Your analysis helps prioritize maintenance and inspection activities."
    ),
    "categories": DISCIPLINE_CATEGORIES["topsides"]
}

def main():
    """Start the A2A Topsides Agent server."""
    print(f"\n{'='*60}")
    print(f"🚀 Starting A2A Topsides Agent")
    print(f"📡 Host: {HOST}")
    print(f"🔌 Port: {PORT}")
    print(f"📋 Categories: {len(AGENT_CONFIG['categories'])} item classes")
    print(f"{'='*60}\n")
    
    # Create A2A server
    app = create_crew_a2a_server(
        **AGENT_CONFIG,
        port=PORT,
        host=HOST,
        file_hash=FILE_HASH
    )
    
    # Run server
    uvicorn.run(
        app.build(), 
        host=HOST, 
        port=PORT,
        log_level="info"
    )

if __name__ == "__main__":
    main()