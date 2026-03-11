# Data Flow Architecture - Agentic Backlog Orchestrator

## Overview

This document explains the complete data pipeline from file upload through caching, processing, and display on the dashboard. It covers both file-based caching (SQLite) and in-memory response caching for chat queries.

---

## 1. File Upload to Dashboard Pipeline

### Step 1: User Uploads Excel File

**Frontend**: `src/components/ChatInterface.jsx` (or upload component)
**Endpoint**: `POST /process-backlog`

```
User selects Excel file (.xls, .xlsx, .xlsm)
   ↓
Frontend sends multipart/form-data to backend:8000/process-backlog
```

### Step 2: File Hash Calculation

**Backend**: `backend/main.py:120-130`

```python
# Calculate SHA256 hash of uploaded file
file_hash = hashlib.sha256(content).hexdigest()
```

**Purpose**: Unique identifier for the file content. Same data = same hash, enables instant cache retrieval.

### Step 3: Cache Check

**Backend**: `backend/database.py:133-163` (`get_cached_data()`)

```python
# Query SQLite database
SELECT * FROM file_cache WHERE file_hash = ?

if row:
    # Cache HIT - return cached data immediately
    return {
        "backlog": cached_backlog,
        "performance": cached_performance,
        "pending": cached_pending,
        "raw_items": all_items,
        "sow_progress": sow_kpis
    }
else:
    # Cache MISS - proceed to parse and process file
```

**SQLite Table Structure** (`file_cache`):
```sql
CREATE TABLE file_cache (
    file_hash TEXT PRIMARY KEY,      -- SHA256 of file
    filename TEXT,                   -- Original filename
    processed_at TEXT,               -- ISO timestamp
    total_items INTEGER,             -- Total count
    backlog_count INTEGER,           -- Backlog=Yes count
    performance_count INTEGER,       -- QCAP/EXDO/Compl count
    sow_progress TEXT,               -- JSON: {month, plan, backlog, site_perf}
    raw_data TEXT                    -- JSON: {items, backlog, performance, pending}
)
```

---

### Step 4: Excel Parsing (If Cache Miss)

**Backend**: `backend/utils.py:read_database_sheet()`

#### 4.1 Sheet Detection
```python
# Find "Data Base" sheet (case-insensitive)
sheet = wb["Data Base"]  # or "database", "DataBase", etc.
```

#### 4.2 Header Mapping (Row 5, Columns B-X)
```python
# Canonical header mapping
canonical_headers = {
    "tag": "Tag",
    "item_class": "Item Class",
    "description": "Description",
    "backlog?": "Backlog?",
    "days_in_backlog": "Days in Backlog",
    "sece": "SECE",
    "order_status": "Order Status",
    "job_done": "Job Done",
    "due_date": "Due Date",
    "pmonth_insp": "PMonth Insp",      # Planned month
    "cmonth_insp": "CMonth Insp",      # Completed month
    # ... 20+ more columns
}
```

#### 4.3 Row Parsing (Starting from Row 6)
```python
all_items = []
for row in sheet.iter_rows(min_row=6, max_row=sheet.max_row):
    item = {}
    for col_idx, canonical in header_map.items():
        cell_value = row[col_idx].value
        item[canonical] = cell_value

    # Stop at 50 consecutive empty rows
    if all(v is None or str(v).strip() == "" for v in item.values()):
        empty_count += 1
        if empty_count >= 50:
            break
    else:
        all_items.append(item)
        empty_count = 0
```

**Result**: List of raw dictionaries (500-1000+ items typically)

---

### Step 5: Data Classification

**Backend**: `backend/main.py:150-175`

Items are split into 3 categories based on business rules:

#### 5.1 Backlog Items
```python
# Rule: Backlog? = "Yes"
backlog_data = [
    item for item in all_items
    if str(item.get('Backlog?', '')).strip().lower() == 'yes'
]
```

#### 5.2 Performance Items
```python
# Rule: (Order Status = QCAP/EXDO) OR (Job Done contains 'Compl')
performance_data = [
    item for item in all_items
    if (
        str(item.get('Order Status', '')).strip().upper() in ['QCAP', 'EXDO']
        or 'compl' in str(item.get('Job Done', '')).lower()
    )
]
```

#### 5.3 Pending Items
```python
# Rule: Order Status in [APPR, INIT, WREL, SWE]
#       AND Backlog? != Yes
#       AND Due Date + 28 days > today
pending_data = [
    item for item in all_items
    if (
        str(item.get('Order Status', '')).strip().upper() in ['APPR', 'INIT', 'WREL', 'SWE']
        and str(item.get('Backlog?', '')).strip().lower() != 'yes'
        and due_date + timedelta(days=28) > datetime.now()
    )
]
```

---

### Step 6: SOW Progress Calculation

**Backend**: `backend/main.py:180-230`

Calculates monthly KPIs from PMonth Insp and CMonth Insp columns:

```python
current_month = datetime.now().month  # e.g., 2 for February

# Plan = items with PMonth Insp = current month
plan_sum = 0
for item in all_items:
    pmonth = str(item.get('PMonth Insp', '')).strip()
    if pmonth.isdigit() and int(pmonth) == current_month:
        plan_sum += 1
    elif pmonth.lower() in ["feb", "february"] and current_month == 2:
        plan_sum += 1

# Site Perf = items with CMonth Insp = current month
perf_sum = 0
for item in all_items:
    cmonth = str(item.get('CMonth Insp', '')).strip()
    if cmonth.isdigit() and int(cmonth) == current_month:
        perf_sum += 1

sow_progress = {
    "month": "FEB",              # Current month abbreviation
    "plan": plan_sum,            # Planned for this month
    "backlog": len(backlog_data),# Total backlog count
    "site_perf": perf_sum        # Completed this month
}
```

---

### Step 7: Cache Storage

**Backend**: `backend/database.py:165-207` (`cache_data()`)

```python
# Store in SQLite file_cache table
raw_data = json.dumps({
    "items": all_items,              # Raw 500+ items
    "backlog": backlog_data,         # Backlog=Yes items
    "performance": performance_data, # Completed items
    "pending": pending_data          # Pending items
})

cursor.execute("""
    INSERT OR REPLACE INTO file_cache
    (file_hash, filename, processed_at, total_items, backlog_count,
     performance_count, sow_progress, raw_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    file_hash,
    filename,
    datetime.now().isoformat(),
    len(all_items),
    len(backlog_data),
    len(performance_data),
    json.dumps(sow_progress),
    raw_data
))
```

**Database Location**: `backend/backlog_cache.db`

---

### Step 8: Return to Frontend

**Backend**: `backend/main.py:245-256`

```python
return ProcessResponse(
    success=True,
    message=f"Successfully processed {len(all_items)} items",
    items_processed=len(all_items),
    dashboard={
        "backlog": backlog_data,      # Array of items
        "performance": performance_data,
        "pending": pending_data,
        "sow_progress": sow_progress  # {month, plan, backlog, site_perf}
    }
)
```

### Step 9: Frontend Renders Dashboard

**Frontend**: `src/App.jsx` (Dashboard component)

```javascript
// Store in state
setDashboardData({
    backlog: response.dashboard.backlog,
    performance: response.dashboard.performance,
    pending: response.dashboard.pending,
    sowProgress: response.dashboard.sow_progress
});

// Render:
// - SOW Progress Chart (Recharts BarChart)
// - Backlog Table (MUI DataGrid)
// - Performance Table (MUI DataGrid)
// - Pending Items Table (MUI DataGrid)
```

---

## 2. Chat Agent RAG Pipeline

When user asks a question in the chat widget, the system uses Retrieval-Augmented Generation (RAG) to answer based on cached data.

### Step 1: User Submits Query

**Frontend**: `src/components/ChatInterface.jsx`
**Endpoint**: `POST /agentic-chat`

```javascript
const response = await axios.post('/agentic-chat', {
    message: "What are the high-risk items?",
    discipline: "topsides",  // or null for all agents
    site: "GIR",             // optional site filter
    items: dashboardData.backlog  // raw items from frontend
});
```

### Step 2: Query Cache Check (In-Memory)

**Backend**: `backend/engineering_agents.py:780-788`

```python
# Build cache key from query parameters
items_hash = hashlib.md5(json.dumps(relevant_items, sort_keys=True).encode()).hexdigest()[:8]
cache_key = _build_cache_key(message, discipline, site, items_hash)
# Example: "5a3c1b2e" (MD5 hash of "what high risk|topsides|GIR|abc12345")

# Check in-memory cache (1-hour TTL)
cached = _get_cached_response(cache_key)
if cached:
    logger.info(f"Cache HIT for query (age: {age}s)")
    return cached  # Instant response, no LLM call
```

**Cache Structure**:
```python
_RESPONSE_CACHE = {
    "5a3c1b2e": {
        "response": {
            "response": "Based on topsides discipline...",
            "agent": "topsides",
            "ai_used": True,
            "items_analyzed": 150
        },
        "timestamp": 1676985234.567
    }
}
```

**TTL**: 1 hour (3600 seconds). After expiration, cache entry is deleted and re-queried.

---

### Step 3: Item Filtering (If Cache Miss)

**Backend**: `backend/engineering_agents.py:750-778`

```python
# Filter items by discipline's item classes
DISCIPLINE_CATEGORIES = {
    "topsides": ["Pressure Vessel (VII)", "Pressure Vessel (VIE)",
                 "Non-Structural Tank", "Structures", "Piping"],
    "psv": ["Pressure Safety Device", "PSV", "Safety Valve"],
    # ... 7 disciplines total
}

relevant_items = [
    item for item in items
    if item.get('Item Class') in DISCIPLINE_CATEGORIES[discipline]
]

# Calculate KPI snapshot
kpi = {
    "total": len(relevant_items),
    "high_risk": count(days_in_backlog > 90 or (SECE and days > 60)),
    "medium_risk": count(30 < days <= 90),
    "low_risk": count(days <= 30),
    "sece_count": count(SECE = True),
    "overdue_count": count(days_in_backlog > 0),
    "backlog_count": count(Backlog? = Yes),
    "completion_rate": completed / total * 100
}
```

---

### Step 4: RAG Context Building

**Backend**: `backend/engineering_agents.py:790-820`

```python
# Prioritize items by risk
prioritized_items = _prioritize_items(relevant_items, limit=20)
# Sorting: High-risk SECE > High-risk > Overdue > Medium-risk > Low-risk

# Include top 5 items (reduced from 15 for performance)
items_summary = _summarize_items_for_prompt(prioritized_items[:5])

# Build context string
context_str = f"""
DATASET SUMMARY (Your Discipline - {disc_info['role']}):
- Total Items: {kpi['total']}
- High Risk: {kpi['high_risk']}
- SECE Items: {kpi['sece_count']}
- Overdue Items: {kpi['overdue_count']}
- Completion Rate: {kpi['completion_rate']}%

RELEVANT INSPECTION ITEMS (Top 5 priority items):
{json.dumps(items_summary, indent=2)}

Use specific data from these items in your answer.
"""
```

---

### Step 5: CrewAI Agent Execution

**Backend**: `backend/engineering_agents.py:826-875`

```python
# Create discipline-specific agent
agent = Agent(
    role="Topsides Integrity Engineer",
    goal="Analyze topsides equipment inspection backlog...",
    backstory="...",
    llm=ChatOpenAI(
        model="openai/gpt-4o-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        temperature=0.2,
        max_tokens=1500
    )
)

# Create task with RAG context
task = Task(
    description=f"""
USER QUESTION: {message}

{context_str}

INSTRUCTIONS:
1. Use only the provided KPIs and items
2. Reference specific Tag IDs and numbers
3. Give at most 3 bullet-level insights
4. Be terse and data-backed
""",
    expected_output="A short, data-driven answer",
    agent=agent
)

# Execute asynchronously
crew = Crew(agents=[agent], tasks=[task], verbose=False)
result = await crew.kickoff_async()

response_payload = {
    "response": result.raw.strip(),
    "agent": "topsides",
    "ai_used": True,
    "items_analyzed": 150
}
```

---

### Step 6: Cache Storage (In-Memory)

**Backend**: `backend/engineering_agents.py:874-875`

```python
# Cache the response before returning
_cache_response(cache_key, response_payload)

# Stored in _RESPONSE_CACHE dictionary with timestamp
```

---

### Step 7: Return to Frontend

**Backend Response**:
```json
{
    "response": "Based on topsides discipline analysis:\n\n- High-risk items: 12 out of 150 total\n- SECE count: 45\n- Tag GIR-PSV-001 is 95 days overdue\n\nRecommendations:\n- Prioritize GIR-PSV-001 immediately\n- Schedule SECE inspections within 30 days",
    "agent": "topsides",
    "ai_used": true,
    "items_analyzed": 150
}
```

### Step 8: Frontend Renders Response

**Frontend**: `src/components/ChatInterface.jsx`

```javascript
// Add message to chat history
setMessages([...messages, {
    sender: 'agent',
    text: response.response,
    timestamp: new Date()
}]);

// Render with ReactMarkdown
<ReactMarkdown remarkPlugins={[remarkGfm]}>
    {response.response}
</ReactMarkdown>
```

**Markdown Rendering**:
- Bullet points: `<ul>`, `<li>`
- Tables: `<table>`, `<th>`, `<td>`
- Code blocks: `<pre>`, `<code>`
- Bold: `**text**` → `<strong>`
- Line spacing: Custom Typography components

---

## 3. Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Upload Excel File  │
                    └─────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    BACKEND PROCESSING                            │
│                                                                  │
│  1. Calculate SHA256 hash                                        │
│     file_hash = sha256(file_content)                             │
│                                                                  │
│  2. Check SQLite Cache (file_cache table)                        │
│     ┌─────────────────────────────────────┐                     │
│     │ Cache HIT?                           │                     │
│     │  YES → Return cached dashboard      │                     │
│     │  NO  → Parse Excel (utils.py)       │                     │
│     └─────────────────────────────────────┘                     │
│                                                                  │
│  3. Excel Parsing (if cache miss)                               │
│     - Find "Data Base" sheet                                    │
│     - Map headers (row 5, cols B-X)                             │
│     - Parse rows starting from row 6                            │
│     - Stop at 50 consecutive empty rows                         │
│     Result: all_items = [500+ dictionaries]                     │
│                                                                  │
│  4. Data Classification                                         │
│     backlog = [item where Backlog?='Yes']                       │
│     performance = [item where Order Status in QCAP/EXDO]        │
│     pending = [item where Order Status in APPR/INIT/WREL]       │
│                                                                  │
│  5. SOW Progress Calculation                                    │
│     plan = count(PMonth Insp == current_month)                  │
│     site_perf = count(CMonth Insp == current_month)             │
│                                                                  │
│  6. Cache Storage (SQLite)                                      │
│     INSERT INTO file_cache                                      │
│     VALUES (file_hash, filename, processed_at, ...)             │
│                                                                  │
│  7. Return Dashboard Data                                       │
│     {backlog, performance, pending, sow_progress}               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND RENDERING                           │
│                                                                  │
│  - Store in React state (dashboardData)                         │
│  - Render MUI DataGrids (3 tables)                              │
│  - Render Recharts BarChart (SOW Progress)                      │
│  - Enable chat widget with cached items                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  User Asks Question │
                    │  in Chat Widget     │
                    └─────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   CHAT AGENT RAG PIPELINE                        │
│                                                                  │
│  1. Build Cache Key                                             │
│     key = MD5(message + discipline + site + items_hash)         │
│                                                                  │
│  2. Check In-Memory Cache (_RESPONSE_CACHE)                     │
│     ┌─────────────────────────────────────┐                     │
│     │ Cache HIT (age < 1 hour)?           │                     │
│     │  YES → Return cached response       │                     │
│     │  NO  → Execute agent with RAG       │                     │
│     └─────────────────────────────────────┘                     │
│                                                                  │
│  3. Filter Items by Discipline                                  │
│     relevant = [item where Item Class in discipline categories] │
│                                                                  │
│  4. Calculate KPIs                                              │
│     {total, high_risk, sece_count, overdue_count, ...}         │
│                                                                  │
│  5. Prioritize Top Items                                        │
│     prioritized = sort_by_risk(relevant)[:5]                    │
│                                                                  │
│  6. Build RAG Context                                           │
│     context = KPI summary + Top 5 items JSON                    │
│                                                                  │
│  7. Execute CrewAI Agent                                        │
│     agent = Topsides Engineer (or PSV, FUIMS, etc.)            │
│     task = Answer user question using context                   │
│     result = await crew.kickoff_async()                         │
│                                                                  │
│  8. Cache Response (In-Memory)                                  │
│     _RESPONSE_CACHE[key] = {response, timestamp}                │
│                                                                  │
│  9. Return to Frontend                                          │
│     {response, agent, ai_used, items_analyzed}                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FRONTEND CHAT RENDERING                        │
│                                                                  │
│  - Add message to chat history                                  │
│  - Render with ReactMarkdown (tables, bullets, code)            │
│  - Apply custom MUI Typography styling                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Caching Strategy Summary

### 4.1 SQLite File Cache (Persistent)

**Purpose**: Cache processed Excel data to avoid re-parsing same files

**Key**: SHA256 hash of file content
**Storage**: `backend/backlog_cache.db` → `file_cache` table
**TTL**: No expiration (manual delete required)
**Data Stored**:
- All raw items (500+ dictionaries)
- Classified views (backlog, performance, pending)
- SOW progress KPIs
- Metadata (filename, processed_at, counts)

**Performance**:
- Cache HIT: ~50ms (database query only)
- Cache MISS: ~3-8 seconds (Excel parsing + processing)

---

### 4.2 In-Memory Response Cache (Volatile)

**Purpose**: Cache agent chat responses to avoid repeated LLM API calls

**Key**: MD5 hash of (message + discipline + site + items_hash)
**Storage**: Python dictionary `_RESPONSE_CACHE` (in-memory)
**TTL**: 1 hour (3600 seconds)
**Data Stored**:
- Agent response text
- Metadata (agent name, items_analyzed, ai_used)
- Timestamp

**Performance**:
- Cache HIT: ~5ms (dictionary lookup)
- Cache MISS: ~3-15 seconds (LLM API call + RAG processing)

**Cache Invalidation**:
- Automatic: After 1-hour TTL expires
- Manual: Restart backend server (clears memory)

---

## 5. Key Optimization Wins

### 5.1 File Upload Optimization
- **Before**: 8 seconds every upload
- **After (cache hit)**: 50ms (160x faster)
- **Reduction**: ~99% latency reduction for repeated files

### 5.2 Chat Query Optimization
- **Before**: 5-15 seconds per query
- **After (cache hit)**: 5ms (1000-3000x faster)
- **Additional Optimizations**:
  - RAG context reduced from 15 to 5 items (30-50% fewer tokens)
  - Response cache eliminates redundant LLM calls
  - Expected: 70-95% faster responses overall

---

## 6. Database Schema Reference

### 6.1 file_cache Table
```sql
CREATE TABLE file_cache (
    file_hash TEXT PRIMARY KEY,
    filename TEXT,
    processed_at TEXT,
    total_items INTEGER,
    backlog_count INTEGER,
    performance_count INTEGER,
    sow_progress TEXT,  -- JSON
    raw_data TEXT       -- JSON: {items, backlog, performance, pending}
);
```

### 6.2 status_history Table
```sql
CREATE TABLE status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_id TEXT,
    new_status TEXT,
    note TEXT,
    timestamp TEXT,
    file_hash TEXT
);
```

### 6.3 a2a_sessions Table (Conversation History)
```sql
CREATE TABLE a2a_sessions (
    session_id TEXT PRIMARY KEY,
    message TEXT,
    disciplines_invoked TEXT,  -- JSON array
    routing_mode TEXT,
    ai_used INTEGER,
    total_duration_ms INTEGER,
    executive_summary TEXT,
    timestamp TEXT
);
```

---

## 7. Next Steps for Enhancement

1. **Conversation History UI**: Load previous chat sessions from `a2a_sessions` table
2. **Dashboard Visualizations**: Add KPI cards, trend charts, critical items spotlight
3. **Lighter UI Design**: Reduce font sizes, padding, colors per Rufus AI screenshot
4. **Thumbs Up/Down**: Add feedback buttons for response quality tracking

---

**Last Updated**: February 20, 2025
**Document Version**: 1.0
