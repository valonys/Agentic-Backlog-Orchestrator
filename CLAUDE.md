# Agentic Backlog Orchestrator - Project Documentation

## /init Checkpoint — 2026-03-11

**Status**: Verified working. Git initialized, secrets protected.

### What was validated
- Backend (FastAPI + CrewAI 1.9.3) starts on port 8000 — health endpoint returns `{"status":"healthy","ai_enabled":true}`
- Frontend (React 18 + Vite 5.1.4) starts on port 5174 — serves SPA with 200 OK
- Vite proxy `/api/*` → `localhost:8000` works correctly
- `.gitignore` protects `backend/.env` (contains real API keys), `node_modules/`, `*.db`, logs, `venv/`
- Git repo initialized on `main` branch

### Quick Start (Development)
```bash
# Terminal 1 — Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 2 — Frontend
npm run dev
```

### Deployment targets
- **GitHub**: Push source code (secrets excluded via .gitignore)
- **Vercel**: Frontend deployment (Vite build → `dist/`)
- **Backend**: Requires separate hosting (Railway, Render, Fly.io) — FastAPI + Python 3.11

---

## Project Overview

**Agentic Backlog Orchestrator** is an AI-powered offshore inspection backlog management system. It processes Excel-based inspection data and provides intelligent analysis through a multi-agent engineering system combined with a modern React dashboard.

### Purpose
- Process complex offshore inspection spreadsheets with hundreds of equipment items
- Automatically categorize items by risk level (High/Medium/Low) and criticality (SECE - Safety & Environmental Critical Equipment)
- Provide discipline-specific engineering analysis through CrewAI agents
- Enable interactive querying of backlog data through AI-powered chat with RAG (Retrieval-Augmented Generation)
- Cache processed results for performance optimization

### Key Use Cases
1. Dashboard visualization of inspection backlogs across multiple offshore sites (GIR, DAL, PAZ, CLV)
2. AI-driven prioritization of critical inspection items
3. Discipline-specific engineering reports (Topsides, FUIMS, PSV, Subsea, Pipeline, Corrosion, Methods)
4. Real-time status tracking and inspection history management

---

## Architecture

### System Architecture Diagram
```
┌──────────────────────────┐
│   React Frontend         │
│   (Vite + Material-UI)   │
│   Port: 5174             │
└──────────────┬───────────┘
               │ HTTP/REST
               ▼
┌──────────────────────────────────────┐
│     FastAPI Backend                  │
│     (Python 3.11+)                   │
│     Port: 8000                       │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Core Endpoints                 │  │
│  │ - /process-backlog             │  │
│  │ - /agentic-report              │  │
│  │ - /agentic-chat                │  │
│  │ - /cache/list, /cache/{hash}   │  │
│  │ - /equipment/{tag_id}          │  │
│  │ - /items/{tag_id}/status       │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Processing Modules             │  │
│  │ - utils.py (Excel parsing)     │  │
│  │ - engineering_agents.py (AI)   │  │
│  │ - database.py (SQLite cache)   │  │
│  │ - models.py (Pydantic)         │  │
│  │ - routing_models.py (Intent)   │  │
│  └────────────────────────────────┘  │
└──────────────┬──────────────────────┬─┘
               │                      │
               ▼                      ▼
        ┌─────────────┐        ┌────────────────┐
        │  openpyxl   │        │ CrewAI 1.9.3   │
        │ (Excel)     │        │ + LangChain    │
        │             │        │ + OpenRouter   │
        └─────────────┘        │ (Discipline    │
                               │  Agents)       │
                               └────────────────┘
                                      │
                                      ▼
                               ┌────────────────┐
                               │ OpenRouter API │
                               │ (gpt-4o-mini)  │
                               └────────────────┘

┌──────────────────────────┐
│ SQLite Cache DB          │
│ (backlog_cache.db)       │
│                          │
│ - file_cache table       │
│ - status_history table   │
│ - equipment_master table │
│ - inspection_history tb  │
└──────────────────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI 0.100.0+
- **Python**: 3.11+
- **Web Server**: Uvicorn 0.23.0+
- **AI/LLM**: 
  - CrewAI 1.9.3 (multi-agent orchestration with async support)
  - LangChain 0.3.27
  - LangChain-OpenAI 0.3.23
  - OpenAI SDK 1.83.0
- **Excel Processing**: openpyxl 3.1.0, pandas 2.0.0
- **Database**: SQLite 3 (via SQLAlchemy 2.0.23)
- **Configuration**: python-dotenv 1.0.0
- **Validation**: Pydantic 2.11.0+, Pydantic-Settings 2.10.0
- **Logging**: python-json-logger 2.0.7
- **Testing**: pytest 8.0.1, pytest-asyncio 0.23.5, httpx 0.27.0

#### Frontend
- **Framework**: React 18.2.0
- **Build Tool**: Vite 5.1.4
- **UI Library**: Material-UI (MUI) 5.15.10
- **Icons**: @mui/icons-material 5.15.10
- **Charts**: Recharts 3.3.0+
- **HTTP Client**: Axios 1.6.7
- **Styling**: @emotion/react 11.11.3, @emotion/styled 11.11.0

#### Containerization & Deployment
- **Docker**: Multi-container orchestration (docker-compose)
- **Backend Container**: Python 3.11 + Uvicorn
- **Frontend Container**: Node.js + Vite dev server

---

## File Structure Overview

```
/Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator/
│
├── CLAUDE.md                          # This documentation
├── README.md                          # User guide
├── docker-compose.yml                 # Multi-container orchestration
├── package.json                       # Root package config
├── vite.config.js                     # Vite configuration
│
├── backend/                           # FastAPI Backend
│   ├── main.py                        # FastAPI app + endpoints
│   ├── models.py                      # Pydantic models
│   ├── utils.py                       # Excel parsing, data processing
│   ├── engineering_agents.py          # CrewAI agent implementation
│   ├── database.py                    # SQLite cache layer
│   ├── routing_models.py              # Intent routing Pydantic models
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment template
│   ├── .env                           # Local environment (not in git)
│   ├── Dockerfile                     # Backend container
│   ├── README_AGENTIC.md              # Agent documentation
│   ├── backlog_cache.db               # SQLite cache database
│   ├── agent_traces.log               # Agent execution traces
│   ├── tests/                         # Test directory
│   │   ├── __init__.py
│   │   └── test_main.py
│   └── venv/                          # Python virtual environment
│
├── src/                               # React Frontend (root-level)
│   ├── main.jsx                       # React entry point + theme
│   ├── App.jsx                        # Main dashboard component
│   └── components/                    # UI components
├── index.html                         # HTML template
├── public/                            # Static assets
│
└── dist/                              # Frontend build output
```

---

## How to Run the Project

### Option 1: Docker (Recommended)

#### Prerequisites
- Docker and Docker Compose installed
- OpenRouter API key from [https://openrouter.ai/keys](https://openrouter.ai/keys)

#### Steps
```bash
cd /Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator

# Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your OPENROUTER_API_KEY

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:5174
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Services:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5174
- Network: backlog-dashboard-network

### Option 2: Manual Setup (Development)

#### Backend Startup

```bash
cd /Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator/backend

# Create/activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add OPENROUTER_API_KEY

# Start backend
python main.py
# OR use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend runs on:** http://localhost:8000

#### Frontend Startup

```bash
cd /Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator

# Install dependencies
npm install

# Start development server
npm run dev

# The app will open at http://localhost:5174
```

**Frontend runs on:** http://localhost:5174

---

## How to Run Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_main.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Frontend Tests

```bash
cd /Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator

# Run tests (if configured)
npm test

# Run with coverage
npm test -- --coverage
```

### Integration Test Script

```bash
cd /Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator

# Make script executable
chmod +x test_agentic.sh

# Run full integration test
./test_agentic.sh
```

---

## Key Environment Variables

### Backend (.env file)

**Required:**
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx    # Your OpenRouter API key from https://openrouter.ai/keys
```

**Optional:**
```env
OPENROUTER_MODEL=minimax/mm-m2               # LLM model (default: openai/gpt-4o-mini in code)
LLM_TEMPERATURE=0.2                          # Model temperature (0.0-1.0)
LLM_MAX_TOKENS=3000                          # Maximum tokens per response
LOG_LEVEL=INFO                               # Logging level (DEBUG, INFO, WARNING, ERROR)
BACKEND_PORT=8000                            # Server port
DEV_RELOAD=false                             # Enable file-watch reload during development
```

### Frontend (.env file - Optional)

```env
VITE_API_URL=http://localhost:8000           # Backend API base URL (default: localhost:8000)
```

### Docker Environment (docker-compose.yml)

```yaml
environment:
  - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}  # Passed from host .env
  - LOG_LEVEL=INFO
  - VITE_API_URL=http://localhost:8000
```

---

## Current Agent Architecture

### Discipline-Specific Agents (CrewAI 1.9.3)

The system implements 7 parallel CrewAI agents, each focused on specific engineering disciplines:

#### 1. **Topsides Engineer**
- **Responsibilities**: Pressure vessels (VII/VIE), non-structural tanks, structures, piping
- **Item Classes**: 
  - Pressure Vessel (VII)
  - Pressure Vessel (VIE)
  - Non-Structural Tank
  - Structures
  - Piping

#### 2. **FUIMS Engineer**
- **Responsibilities**: Fire & Gas systems, emergency shutdown, safety instrumentation
- **Item Classes**:
  - FU Items
  - Fire & Gas
  - Emergency Shutdown
  - Safety System

#### 3. **PSV Engineer**
- **Responsibilities**: Pressure safety devices, relief valves
- **Item Classes**:
  - Pressure Safety Device
  - PSV
  - Safety Valve
  - Relief Valve

#### 4. **Subsea Engineer**
- **Responsibilities**: Subsea infrastructure, trees, manifolds, umbilicals
- **Item Classes**:
  - Subsea
  - XMAS Tree
  - Christmas Tree
  - Manifold
  - Umbilical

#### 5. **Pipeline/ILI Engineer**
- **Responsibilities**: Intelligent pigging, inline inspection
- **Item Classes**:
  - Intelligent Pigging
  - ILI
  - Pigging
  - Pipeline Inspection

#### 6. **Corrosion Engineer**
- **Responsibilities**: Corrosion monitoring, coating, cathodic protection
- **Item Classes**:
  - Corrosion Monitoring
  - Corrosion
  - Coating
  - Cathodic Protection
  - CP

#### 7. **Methods & Procedures Engineer**
- **Responsibilities**: Cross-discipline methods, procedures, standards
- **Item Classes**:
  - Method
  - Procedure
  - Standard
  - Specification

### CrewAI Integration Details

**Version**: CrewAI 1.9.3 with async support

**Key Features Used:**
- **Async Kickoff**: `await crew.kickoff_async()` for non-blocking agent execution
- **Hierarchical Process**: Agents work in parallel, then synthesize results
- **JSON Output**: `task.output_json` with Pydantic model enforcement
- **Guardrails**: Structured JSON validation for report outputs
- **Fallback Mode**: Automatic template-based fallback if AI is unavailable

**Process Flow:**
1. Receive items from Excel upload
2. Filter items by discipline-specific item classes
3. Calculate KPI snapshot for each discipline:
   - Total items in discipline
   - High/Medium/Low risk counts
   - SECE count
   - Overdue count
   - Backlog vs. pending vs. completed
   - Completion rate
4. Create agent with role, goal, backstory
5. Create task with constraints (terse output, max 3-5 points per section)
6. Execute crew asynchronously
7. Parse CrewOutput (json_dict first, then raw)
8. Validate JSON structure
9. Push summary to memory for context
10. Log trace for debugging

### Routing & Intent Models (routing_models.py)

Lightweight models for potential intelligent routing:

**Core Models:**
- `QueryIntent`: User's question parsed into task types, entities, scope
- `RoutingDecision`: Where to route the query (which disciplines)
- `RoutingCandidate`: Candidate discipline with scoring
- `SelectedDiscipline`: Final selected discipline for execution
- `ScopeFilter`: Dynamic filtering by field/operator/value
- `EvidenceProbe`: Metadata about retrieved evidence quality

**Currently Used For:**
- Chat endpoint discipline selection
- Future extensibility for intelligent multi-agent routing

---

## API Endpoints Summary

### Health & Metadata

#### `GET /`
**Health check endpoint**

```json
Response:
{
  "status": "healthy",
  "service": "Backlog Inspector API",
  "version": "2.0.0",
  "ai_enabled": true
}
```

### Processing Endpoints

#### `POST /process-backlog`
**Process Excel backlog file and generate dashboard data**

Request:
- Content-Type: `multipart/form-data`
- Body: Excel file (.xls, .xlsx, .xlsm) with "Data Base" sheet
- **Filename Requirements**: Must start with valid site prefix (GIR, DAL, PAZ, or CLV)
  - Valid: `GIR_Database.xlsm`, `DAL_Backlog_2025.xlsx`, `PAZ_Inspection.xls`
  - Invalid: `ABC_Database.xlsx`, `Backlog.xlsm`

```json
Response (200):
{
  "success": true,
  "message": "Successfully processed 778 items (150 backlog, 250 performance, 100 pending)",
  "items_processed": 778,
  "dashboard": {
    "backlog": [...],           // Backlog=Yes items
    "performance": [...],       // QCAP/EXDO or Job Done=Compl
    "pending": [...],           // Order Status in APPR/INIT/WREL/SWE, Backlog=No
    "sow_progress": {
      "month": "FEB",
      "plan": 42,               // PMonth Insp count
      "backlog": 150,           // Backlog? = Yes count
      "site_perf": 35           // CMonth Insp count
    }
  },
  "timestamp": "2025-02-19T..."
}
```

#### `POST /agentic-report`
**Run multi-agent engineering analysis**

Request:
- Content-Type: `multipart/form-data`
- Body: Excel file (.xls, .xlsx, .xlsm)

```json
Response (200):
{
  "success": true,
  "message": "Agentic analysis completed for 778 items",
  "items_processed": 778,
  "agentic": {
    "timestamp": "2025-02-19T...",
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
          "backlog_count": 80,
          "pending_count": 20,
          "completed_count": 50,
          "completion_rate": 33.3
        },
        "item_count": 150,
        "report": {
          "summary": "...",
          "key_findings": ["...", "..."],
          "recommendations": ["...", "..."],
          "critical_items": [
            {
              "tag_id": "GIR-PSV-001",
              "risk": "High",
              "days_overdue": 95,
              "sece": true
            }
          ],
          "trends": "..."
        },
        "ai_used": true
      },
      "fuims": {...},
      "psv": {...},
      "subsea": {...},
      "pipeline": {...},
      "corrosion": {...},
      "methods": {...}
    }
  }
}
```

#### `POST /agentic-chat`
**Chat with engineering agents using RAG**

Request:
```json
{
  "message": "What are the high-risk items?",
  "discipline": "topsides",     // Optional: null for all agents
  "site": "GIR",                // Optional: site filter for cache
  "items": [...],               // Optional: raw items for RAG
  "context": {}                 // Optional: additional context
}
```

Response:
```json
{
  "response": "Based on the topsides discipline analysis, ...",
  "agent": "topsides",
  "ai_used": true,
  "discipline": "topsides",
  "context": {...}
}
```

### Cache Management

#### `GET /cache/list`
**List all cached files**

Query Parameters:
- `site` (optional): Filter by site prefix (GIR, DAL, PAZ, CLV)

```json
Response:
{
  "success": true,
  "files": [
    {
      "file_hash": "abc123...",
      "filename": "GIR_Database.xlsm",
      "processed_at": "2025-02-19T10:30:00",
      "total_items": 778,
      "backlog_count": 150,
      "performance_count": 250
    }
  ]
}
```

#### `GET /cache/{file_hash}`
**Load data from cache by hash**

Response: ProcessResponse (same structure as /process-backlog)

### Status Management

#### `GET /items/{tag_id}/status`
**Get status history for a tag**

```json
Response:
{
  "tag_id": "GIR-PSV-001",
  "history": [
    {
      "tag_id": "GIR-PSV-001",
      "new_status": "In Progress",
      "note": "Started inspection",
      "timestamp": "2025-02-15T10:00:00"
    },
    {
      "tag_id": "GIR-PSV-001",
      "new_status": "Completed",
      "note": "Inspection passed",
      "timestamp": "2025-02-18T15:30:00"
    }
  ]
}
```

#### `POST /items/{tag_id}/status`
**Add status update for a tag**

Request:
```json
{
  "tag_id": "GIR-PSV-001",
  "new_status": "In Progress",
  "note": "Started inspection"
}
```

Response: StatusHistory (same as GET endpoint)

### Equipment Master Data (SAP-like)

#### `GET /equipment/{tag_id}`
**Get complete equipment detail with history**

```json
Response:
{
  "equipment": {
    "tag_id": "GIR-PSV-001",
    "functional_location": "GIR/TOPSIDES/SYSTEMS/...",
    "equipment_category": "Pressure Safety Device",
    "description": "Main Relief Valve",
    "system": "Pressure Relief",
    "location": "TOPSIDES",
    "manufacturing_details": "...",
    "fluid_service": "Oil",
    "backlog_tracker": "...",
    "inspections_done": "5",
    "history_comments": "...",
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-02-19T00:00:00",
    "created_by": "System",
    "updated_by": "Engineer"
  },
  "inspection_history": [...],
  "status_history": [...]
}
```

#### `POST /equipment`
**Create or update equipment master data**

Request:
```json
{
  "tag_id": "GIR-PSV-001",
  "equipment_category": "Pressure Safety Device",
  "description": "Main Relief Valve",
  "system": "Pressure Relief",
  "location": "TOPSIDES"
}
```

#### `POST /equipment/{tag_id}/inspection`
**Add inspection record to equipment**

Request:
```json
{
  "inspection_date": "2025-02-18",
  "inspection_type": "Visual",
  "result": "Pass",
  "inspector": "John Doe",
  "notes": "No defects found"
}
```

---

## Important Patterns & Conventions

### 1. Data Processing Pipeline

**Flow:**
1. File upload → Hash (SHA256)
2. Check cache for hash match
3. If cached, refresh dashboard views from cached raw items
4. If not cached:
   - Parse Excel "Data Base" sheet (rows 6+, columns B-X)
   - Extract ALL items (backlog, performance, pending)
   - Process each dataset separately
   - Calculate SOW Progress metrics
   - Cache raw items + processed results

### 2. Excel Sheet Parsing

**Location**: Hardcoded to sheet "Data Base" (case-insensitive, allows spacing)
**Preprocessing**:
- Rows 1-4 are skipped (metadata/title rows)
- Column A is skipped (unused column)
- Row 5 becomes the header row (columns B-X)
- Data starts from row 6

**Header Row**: Row 5, columns B-X (after preprocessing)
**Data Rows**: Start from row 6 (after preprocessing)
**Column Mapping**: Canonical header mapping in `utils.py:map_headers()`
**Detection**: Stops at 50 consecutive empty rows
**Date Formatting**: Due Date column is formatted as YYYY-MM-DD

**Filename Validation**:
- Files must follow naming pattern: `{SITE}_*.xlsx`
- Valid site prefixes: GIR, DAL, PAZ, CLV
- Validation performed in `utils.py:validate_filename_pattern()`

**Required Columns:**
- `Tag`: Equipment identifier
- `Backlog?`: "Yes"/"No" for backlog status
- `Days in Backlog`: Integer days overdue
- `Due Date`: Date field (formatted as YYYY-MM-DD)

**Key Columns:**
- `Item Class`: Type of inspection (mapped to disciplines)
- `SECE`: Boolean for Safety/Environmental Critical Equipment
- `Order Status`: Status code (APPR, INIT, WREL, QCAP, EXDO, etc.)
- `Job Done`: Completion status

### 3. Item Classification

**Backlog Items:**
```python
Backlog? == "Yes"
```

**Performance Items:**
```python
(Order Status in ['QCAP', 'EXDO']) OR (Job Done contains 'Compl')
```

**Pending Items:**
```python
Order Status in ['APPR', 'INIT', 'WREL', 'SWE'] AND Backlog? != 'Yes'
AND Due Date + 28 days > today
```

### 4. Risk Level Calculation

```python
HIGH_RISK = Days in Backlog > 90 OR (SECE AND Days in Backlog > 60)
MEDIUM_RISK = 30 < Days in Backlog <= 90
LOW_RISK = Days in Backlog <= 30
```

### 5. SOW Progress Metrics (Current Month)

Parsed from PMonth Insp (Planned Month) and CMonth Insp (Completed Month):
- Supports numeric (1-12) and month names
- `plan` = count of items with PMonth Insp = current month
- `backlog` = total count where Backlog? = "Yes"
- `site_perf` = count of items with CMonth Insp = current month

### 6. Agent Output Validation

**Guardrail Structure:**
```python
{
  "summary": str,                    # Max 2 sentences
  "key_findings": List[str],         # Max 3 items, <=20 words each
  "recommendations": List[str],      # Max 3 items, <=20 words each
  "critical_items": List[Dict],      # Up to 5 items
  "trends": str                      # 1 sentence
}
```

Each critical_item requires: `tag_id`, `risk`, `days_overdue`, `sece`

### 7. Caching Strategy

**Database**: SQLite (backlog_cache.db)

**Tables:**
- `file_cache`: Stores processed results by file_hash
- `status_history`: User status updates per tag
- `equipment_master`: Equipment reference data
- `inspection_history`: Inspection records per tag

**Cache Hit Logic:**
- Calculate file SHA256
- Query for existing record
- If found, reload dashboard from cached raw_items (recomputes views)
- Fallback: Use cached backlog/performance/pending directly

### 8. Async/Await Patterns

CrewAI 1.9.3 Integration:
```python
result = await crew.kickoff_async()  # Non-blocking agent execution

# Result is CrewOutput object:
if hasattr(result, 'json_dict') and result.json_dict:
    report = result.json_dict
else:
    report_str = result.raw or str(result)
    report = json.loads(report_str)
```

### 9. Environment Loading

**Backend**: Loads from `backend/.env` explicitly
```python
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)
```

**Fallback**: Returns warnings if API key missing, but app continues (AI disabled)

### 10. CORS Configuration

**Allowed Origins:**
- http://localhost:5173
- http://localhost:5174
- http://localhost:5175
- http://localhost:5176
- http://localhost:3000

**Methods**: All
**Credentials**: Allowed

---

## Known Tech Stack Versions

### Backend Dependencies (from requirements.txt)

**Web Framework:**
- fastapi>=0.100.0,<0.111.0
- uvicorn[standard]>=0.23.0
- python-multipart>=0.0.9

**Excel Processing:**
- openpyxl>=3.1.0
- pandas>=2.0.0

**AI/LLM (CrewAI Stack):**
- crewai==1.9.3
- crewai-tools==1.9.3
- langchain-openai==0.3.23
- langchain==0.3.27
- openai==1.83.0

**Configuration & Validation:**
- python-dotenv>=1.0.0
- pydantic>=2.11.0,<3.0.0
- pydantic-settings>=2.10.0

**Database & Caching:**
- sqlalchemy==2.0.23

**Logging:**
- python-json-logger==2.0.7

**Testing:**
- pytest==8.0.1
- pytest-asyncio==0.23.5
- httpx>=0.27.0

### Frontend Dependencies

**Runtime:**
- react@18.2.0
- react-dom@18.2.0
- @mui/material@5.15.10
- @mui/icons-material@5.15.10
- recharts@3.3.0+
- axios@1.6.7
- @emotion/react@11.11.3
- @emotion/styled@11.11.0

**Build & Dev:**
- vite@5.1.4
- @vitejs/plugin-react@4.2.1
- eslint@8.56.0
- @types/react@18.2.56
- @types/react-dom@18.2.19

---

## Common Development Tasks

### Add a New Discipline Agent

1. **Update DISCIPLINE_CATEGORIES** in `engineering_agents.py`:
```python
DISCIPLINE_CATEGORIES = {
    "new_discipline": [
        "Item Class 1",
        "Item Class 2",
    ]
}
```

2. **Create agent definition** (in `run_engineering_agents` function):
```python
result = await _run_discipline_agent(
    items,
    discipline="new_discipline",
    role="Your Engineer",
    goal="...",
    backstory="...",
    categories=DISCIPLINE_CATEGORIES["new_discipline"]
)
```

3. **Add to discipline routing** (for chat):
```python
"new_discipline": ["keyword1", "keyword2"]
```

### Modify Excel Column Mapping

1. Edit `map_headers()` in `utils.py`
2. Add new canonical header name
3. Update parsing logic if needed
4. Test with sample Excel file

### Change AI Model

Edit `engineering_agents.py`:
```python
llm = ChatOpenAI(
    model="openai/gpt-4-turbo",  # Change this
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
    temperature=0.3,
    max_tokens=2000
)
```

### Enable Development Reload

```bash
# In backend/.env
DEV_RELOAD=true

# Then run
python main.py
# Or docker-compose
docker-compose up --build
```

---

## Troubleshooting & Common Issues

### "OPENROUTER_API_KEY not set"
- Copy .env.example to .env
- Add your actual API key
- Backend will warn but continue with fallback mode

### "No sheet named 'Data Base' found"
- Check Excel file has "Data Base" sheet (case-insensitive)
- Allowed variations: "Data Base", "database", "DataBase"

### "Port 8000 already in use"
```bash
# Find process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --port 8001
```

### Frontend can't connect to backend
- Ensure backend is running: `curl http://localhost:8000/`
- Check CORS configuration in `main.py`
- Verify API_URL in `App.jsx` matches backend URL

### CrewAI async errors
- Ensure Python 3.10+
- Update CrewAI to 1.9.3
- Check OpenRouter API key validity

### Cache not clearing
```bash
# Remove cache database
rm backend/backlog_cache.db

# Backend will recreate on next run
```

---

## Future Enhancements

- [ ] Multi-user authentication & RBAC
- [ ] Historical trend analysis across months
- [ ] Email notifications for high-risk items
- [ ] SAP integration for maintenance systems
- [ ] Mobile app (React Native)
- [ ] PDF/Excel report generation
- [ ] Advanced filtering & search
- [ ] Bulk actions on dashboard
- [ ] GraphQL API option
- [ ] WebSocket live updates

---

## Key Entry Points

**Backend Entry**: `/Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator/backend/main.py`

**Frontend Entry**: `/Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator/src/main.jsx`

**Project Root**: `/Users/atalibamiguel/Documents/Agentic_Backlog_Orchestrator`

**Documentation Files**:
- `CLAUDE.md` (this file) - Technical deep-dive
- `README.md` - User guide
- `backend/README_AGENTIC.md` - Agent-specific docs

---

**Last Updated**: March 12, 2026
**Project Version**: 2.0.0
**Agentic System**: CrewAI 1.9.3 with async/hierarchical processes
**Author**: Ataliba Miguel

---

**Powered by SPT/INSP/MET | Contact: Ataliba Miguel**
