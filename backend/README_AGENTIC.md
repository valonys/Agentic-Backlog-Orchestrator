# Multi-Agent Engineering Analysis

## Overview
The engineering agents module provides discipline-specific analysis of inspection backlog items using CrewAI agents. Each discipline focuses on specific equipment categories and generates structured KPI reports.

## Requirements

### Python Version
**Python 3.10+ is required** for CrewAI support. Python 3.9 and below will use fallback (non-AI) mode.

### Dependencies
Install AI dependencies:
```bash
cd backend
source venv/bin/activate
pip install crewai langchain-openai langchain openai
```

### Environment Variables
Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

Or add to `.env` file:
```
OPENROUTER_API_KEY=your-api-key-here
```

## Disciplines

The system includes 7 discipline-specific agents:

1. **Topsides Engineer** — Pressure vessels (VII/VIE), non-structural tanks, structures, piping
2. **FUIMS Engineer** — FU items plus fire, gas, and emergency shutdown instrumentation
3. **PSV Engineer** — Pressure safety devices, relief/safety valves
4. **Subsea Engineer** — Xmas trees, manifolds, umbilicals, subsea infrastructure
5. **Pipeline / Intelligent Pigging Engineer** — Intelligent pigging, ILI, pipeline inspection
6. **Corrosion Engineer** — Corrosion monitoring, coating/cathodic protection
7. **Methods & Procedures Engineer** — Cross-discipline methods, procedures, standards compliance

## API Endpoint

### POST `/agentic-report`

Upload an Excel file to generate discipline-specific engineering reports.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: Excel file (`.xls`, `.xlsx`, `.xlsm`)

**Response:**
```json
{
  "success": true,
  "message": "Agentic analysis completed for X items",
  "items_processed": 778,
  "agentic": {
    "timestamp": "2025-01-28T...",
    "total_items": 778,
    "disciplines_analyzed": 7,
    "ai_enabled": true,
    "ai_used_count": 7,
    "reports": {
      "topsides": {
        "discipline": "topsides",
        "kpi": {
          "total": 150,
          "high_risk": 10,
          "medium_risk": 25,
          "low_risk": 115,
          "sece_count": 45,
          "overdue_count": 35,
          "completion_rate": 85.5
        },
        "item_count": 150,
        "report": {
          "summary": "...",
          "key_findings": ["...", "..."],
          "recommendations": ["...", "..."],
          "critical_items": [...],
          "trends": "..."
        },
        "ai_used": true
      },
      ...
    }
  }
}
```

## Fallback Mode

If AI libraries are not available or API key is missing, the system automatically falls back to rule-based analysis:
- KPI snapshots are still calculated
- Reports use template-based summaries
- `ai_used` flag is set to `false`

## Testing

Test the endpoint with curl:
```bash
curl -X POST "http://localhost:8000/agentic-report" \
  -F "database=@path/to/your/file.xlsm"
```

Or use the FastAPI docs at `http://localhost:8000/docs` to test interactively.
