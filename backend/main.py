"""
Backlog Inspector Dashboard - FastAPI Backend
Processes Excel files containing inspection backlog data
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import asyncio

from utils import read_database_sheet, process_with_ai, process_backlog_items, process_performance_items, process_pending_items
from models import BacklogItem, DashboardItem, ProcessResponse, StatusUpdate, StatusHistory, EquipmentMaster, EquipmentDetail, InspectionRecord, ChatRequest
from database import calculate_file_hash, get_cached_data, cache_data, save_status_update, get_status_history, list_cached_files, get_equipment, save_equipment, get_inspection_history, add_inspection_record
from engineering_agents import run_engineering_agents, chat_with_agent
from a2a_protocol import AGENT_CARDS
from a2a_orchestrator import orchestrate as a2a_orchestrate_fn
from database import save_a2a_session, log_agent_call, get_a2a_session_history, save_chat_feedback, get_chat_feedback_stats, list_chat_feedback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
# Load from backend directory explicitly
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Validate required environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY not set - AI enrichment will be disabled")

# Initialize FastAPI app
app = FastAPI(
    title="Backlog Inspector API",
    version="2.0.0",
    description="Process offshore inspection backlog data with AI-powered insights"
)
# In-memory status store: { tag_id: [StatusUpdate, ...] }
from threading import Lock
_status_lock = Lock()
_status_store: dict[str, list[StatusUpdate]] = {}


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Backlog Inspector API",
        "version": "2.0.0",
        "ai_enabled": bool(OPENROUTER_API_KEY)
    }

@app.post("/process-backlog", response_model=ProcessResponse)
async def process_backlog(database: UploadFile = File(...)):
    """
    Process uploaded Excel database file containing inspection backlog

    File Requirements:
    - Must start with site prefix: GIR_, DAL_, PAZ_, or CLV_
    - Must contain 'Data Base' sheet
    - Format: Rows 1-4 are metadata (ignored), Row 5 is headers, Data starts Row 6
    - Column A is ignored, data in columns B-X

    Args:
        database: Excel file (.xls, .xlsx, .xlsm) with "Data Base" sheet

    Returns:
        ProcessResponse with dashboard data and metadata
    """
    # Validate file extension
    allowed_extensions = ('.xls', '.xlsx', '.xlsm')
    if not database.filename.endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Validate filename pattern (must start with GIR, DAL, PAZ, or CLV)
    from utils import validate_filename_pattern
    is_valid, result = validate_filename_pattern(database.filename)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filename pattern. {result}"
        )

    logger.info(f"Filename validation passed: Site={result}")
    
    # Save uploaded file temporarily
    db_path = f"/tmp/{database.filename}"
    logger.info(f"Processing file: {database.filename}")
    
    try:
        # Save file
        with open(db_path, "wb") as f:
            content = await database.read()
            f.write(content)
        
        logger.info(f"File saved to {db_path}, size: {len(content)} bytes")
        
        # Check cache first
        file_hash = calculate_file_hash(db_path)
        cached = get_cached_data(file_hash)
        
        if cached:
            logger.info("Using cached data - refreshing dashboard views")
            raw_items = cached.get("raw_items")
            if raw_items:
                logger.info("Recomputing backlog, performance, and pending from cached raw items")
                backlog_data = process_backlog_items(raw_items)
                performance_data = process_performance_items(raw_items)
                pending_data = process_pending_items(raw_items)
                items_total = len(raw_items)
            else:
                backlog_data = cached["backlog"]
                performance_data = cached["performance"]
                pending_data = cached.get("pending", [])
                items_total = cached["items_processed"]

            # Ensure sow_progress is properly formatted
            sow_progress_data = cached.get("sow_progress")
            if not sow_progress_data:
                sow_progress_data = {
                    "month": datetime.now().strftime("%b").upper(),
                    "plan": 0,
                    "backlog": len(backlog_data),
                    "site_perf": 0
                }
            elif isinstance(sow_progress_data, str):
                import json
                sow_progress_data = json.loads(sow_progress_data)

            logger.info(f"Cached SOW Progress: {sow_progress_data}")
            return ProcessResponse(
                success=True,
                message=f"Loaded from cache: {items_total} items ({len(backlog_data)} backlog, {len(performance_data)} performance, {len(pending_data)} pending)",
                items_processed=items_total,
                dashboard={
                    "backlog": backlog_data,
                    "performance": performance_data,
                    "pending": pending_data,
                    "sow_progress": sow_progress_data
                }
            )
        
        logger.info("Cache miss - processing file...")
        # Parse Excel file - now gets ALL items
        all_items = read_database_sheet(db_path)
        logger.info(f"Extracted {len(all_items)} total items from database")

        if not all_items:
            return ProcessResponse(
                success=True,
                message="No items found in database",
                items_processed=0,
                dashboard={
                    "backlog": [],
                    "performance": [],
                    "pending": [],
                    "sow_progress": {
                        "month": datetime.now().strftime("%b").upper(),
                        "plan": 0,
                        "backlog": 0,
                        "site_perf": 0
                    }
                }
            )

        # Process Backlog, Performance, and Pending datasets
        logger.info("Processing Backlog items (Backlog='Yes')")
        backlog_data = process_backlog_items(all_items)

        logger.info("Processing Performance items (QCAP/EXDO with Job Done=Compl)")
        performance_data = process_performance_items(all_items)

        logger.info("Processing Pending items (Backlog='No' with Order Status in APPR/WREL/INIT)")
        pending_data = process_pending_items(all_items)

        # Calculate SOW Progress metrics for current month
        from datetime import datetime
        current_month = datetime.now().month
        backlog_count = len([item for item in all_items if item.get('Backlog?') == 'Yes'])
        
        # Sum PMonth Insp and CMonth Insp for current month
        # Handle various formats: numeric (1-12), string numbers, or month names
        plan_sum = 0
        perf_sum = 0
        month_names = ['jan', 'january', 'feb', 'february', 'mar', 'march', 'apr', 'april',
                      'may', 'jun', 'june', 'jul', 'july', 'aug', 'august', 'sep', 'september',
                      'oct', 'october', 'nov', 'november', 'dec', 'december']
        current_month_name = datetime.now().strftime("%b").lower()
        
        for item in all_items:
            try:
                # PMonth Insp - planned month
                pmonth = str(item.get('PMonth Insp', '')).strip()
                if pmonth:
                    # Try numeric
                    if pmonth.isdigit():
                        if int(pmonth) == current_month:
                            plan_sum += 1
                    # Try month name match
                    elif pmonth.lower() in month_names:
                        month_idx = month_names.index(pmonth.lower()) // 2 + 1
                        if month_idx == current_month:
                            plan_sum += 1
                
                # CMonth Insp - completed month
                cmonth = str(item.get('CMonth Insp', '')).strip()
                if cmonth:
                    # Try numeric
                    if cmonth.isdigit():
                        if int(cmonth) == current_month:
                            perf_sum += 1
                    # Try month name match
                    elif cmonth.lower() in month_names:
                        month_idx = month_names.index(cmonth.lower()) // 2 + 1
                        if month_idx == current_month:
                            perf_sum += 1
            except (ValueError, TypeError, AttributeError):
                continue
        
        sow_progress = {
            "month": datetime.now().strftime("%b").upper(),
            "plan": plan_sum,
            "backlog": backlog_count,
            "site_perf": perf_sum
        }
        
        logger.info(f"SOW Progress for {sow_progress['month']}: Plan={plan_sum}, Backlog={backlog_count}, Site Perf={perf_sum}")

        # Cache the results
        cache_data(
            file_hash=file_hash,
            filename=database.filename,
            backlog_data=backlog_data,
            performance_data=performance_data,
            pending_data=pending_data,
            sow_progress=sow_progress,
            total_items=len(all_items),
            raw_items=all_items
        )

        logger.info(f"Returning dashboard with sow_progress: {sow_progress}")
        return ProcessResponse(
            success=True,
            message=f"Successfully processed {len(all_items)} items ({len(backlog_data)} backlog, {len(performance_data)} performance, {len(pending_data)} pending)",
            items_processed=len(all_items),
            dashboard={
                "backlog": backlog_data,
                "performance": performance_data,
                "pending": pending_data,
                "sow_progress": sow_progress
            }
        )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary file
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Cleaned up temporary file: {db_path}")




@app.post("/agentic-report")
async def agentic_report(database: UploadFile = File(...)):
    """
    Run the multi-agent engineering analysis on the uploaded Excel database.
    Returns discipline-focused KPI reports without altering existing dashboard data.
    """
    allowed_extensions = ('.xls', '.xlsx', '.xlsm')
    if not database.filename.endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    db_path = f"/tmp/{database.filename}"
    logger.info(f"Agentic analysis for file: {database.filename}")

    try:
        with open(db_path, "wb") as f:
            content = await database.read()
            f.write(content)

        logger.info(f"File saved to {db_path}, size: {len(content)} bytes")
        items = read_database_sheet(db_path)
        logger.info(f"Parsed {len(items)} items for agentic analysis")

        reports = await run_engineering_agents(items)
        message = f"Agentic analysis completed for {len(items)} items"
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": message,
                "items_processed": len(items),
                "agentic": reports,
            },
        )
    except ValueError as ve:
        logger.error(f"Validation error during agentic analysis: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Agentic analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agentic analysis failed: {str(e)}"
        )
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Cleaned up temporary file: {db_path}")


@app.post("/agentic-chat")
async def agentic_chat(request: ChatRequest):
    """
    Chat with engineering agents about inspection backlog using RAG.

    Supports Server-Sent Events (SSE) for streaming responses.

    Request body:
    {
        "message": "What are the high-risk items?",
        "discipline": "topsides" (optional, null for all agents),
        "site": "GIR" (optional),
        "items": [...] (optional, raw items from frontend for RAG),
        "context": {} (optional),
        "stream": true (optional, enables SSE streaming)
    }
    """
    try:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        discipline = request.discipline
        site = request.site
        context = request.context or {}
        items = request.items  # Items sent from frontend
        stream = getattr(request, 'stream', False)  # Check if streaming requested

        # If items not provided from frontend, try to get from cache filtered by site
        if not items:
            try:
                # Load site-specific cache if site is provided
                cached_files = list_cached_files(site=site) if site else list_cached_files()
                if cached_files:
                    # Use most recent cache for the site
                    most_recent = cached_files[0]

                    # Validate site match if site is specified
                    if site:
                        filename_prefix = most_recent.get("filename", "").upper()[:3]
                        if filename_prefix != site.upper():
                            logger.warning(f"Cache mismatch: file {most_recent.get('filename')} belongs to {filename_prefix}, not {site}")
                            # Try to find a matching file
                            matching_file = next((f for f in cached_files if f.get("filename", "").upper()[:3] == site.upper()), None)
                            if matching_file:
                                most_recent = matching_file
                            else:
                                logger.warning(f"No cached file found for site {site}")
                                cached_files = []

                    if cached_files:
                        cached = get_cached_data(most_recent["file_hash"])
                        if cached:
                            items = cached.get("raw_items")
                            if items:
                                context["total_items"] = len(items)
                                context["has_data"] = True
                                logger.info(f"Loaded {len(items)} items from {site or 'all'} site cache for RAG")
            except Exception as e:
                logger.warning(f"Could not load cached data for chat context: {str(e)}")

        if not items:
            logger.warning("No items available for RAG - responses will be generic")

        logger.info(f"Chat request: discipline={discipline}, site={site}, message_length={len(message)}, items_count={len(items) if items else 0}, stream={stream}")

        # If streaming is requested, use SSE
        if stream:
            async def event_generator():
                try:
                    # Get complete response first (CrewAI doesn't support true streaming)
                    response = await chat_with_agent(
                        message=message,
                        discipline=discipline,
                        items=items,
                        context=context,
                        site=site,
                        model_id=request.model_id,
                    )

                    # Simulate streaming by breaking response into chunks
                    response_text = response.get("response", "")
                    agent = response.get("agent", "system")
                    ai_used = response.get("ai_used", False)

                    # Send metadata first
                    yield f"data: {json.dumps({'agent': agent, 'ai_used': ai_used, 'type': 'metadata'})}\n\n"
                    await asyncio.sleep(0.01)

                    # Stream text word-by-word for smooth UI experience
                    words = response_text.split()
                    for i, word in enumerate(words):
                        chunk_text = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'content': chunk_text, 'type': 'content'})}\n\n"
                        await asyncio.sleep(0.02)  # 20ms delay for smooth streaming

                    # Send completion event
                    yield f"data: {json.dumps({'done': True, 'type': 'done'})}\n\n"

                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming response
            response = await chat_with_agent(
                message=message,
                discipline=discipline,
                items=items,
                context=context,
                site=site,
                model_id=request.model_id,
            )

            return JSONResponse(
                status_code=200,
                content=response
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )


# ---- A2A Endpoints ----

class A2AOrchestrationRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User query to route and answer")
    site: Optional[str] = Field(None, description="Site filter: GIR, DAL, PAZ, CLV")
    session_id: Optional[str] = Field(None, description="Resume or label a session")
    disciplines: Optional[List[str]] = Field(None, description="Limit to specific disciplines")
    model_id: Optional[str] = Field(None, description="Model catalogue key, e.g. 'openrouter/gpt-4o-mini'")


@app.get("/a2a/models")
async def get_model_catalogue():
    """Return available LLM models grouped by provider, with availability flags."""
    from a2a_orchestrator import MODEL_CATALOGUE, _DEFAULT_MODEL_ID
    providers = {
        "openrouter": {"label": "OpenRouter", "key_env": "OPENROUTER_API_KEY"},
        "deepseek":   {"label": "DeepSeek",   "key_env": "DEEPSEEK_API_KEY"},
        "anthropic":  {"label": "Anthropic",  "key_env": "ANTHROPIC_API_KEY"},
        "gemini":     {"label": "Gemini",     "key_env": "GEMINI_API_KEY"},
    }
    models = []
    for model_id, entry in MODEL_CATALOGUE.items():
        provider = entry["provider"]
        has_key = bool(os.getenv(providers[provider]["key_env"], "").strip())
        models.append({
            "id": model_id,
            "label": model_id.split("/", 1)[-1],  # e.g. "gpt-4o-mini", "deepseek-chat"
            "provider": provider,
            "provider_label": providers[provider]["label"],
            "available": has_key,
        })
    return {"models": models, "default": _DEFAULT_MODEL_ID}


@app.get("/a2a/agents")
async def get_agent_cards():
    """
    A2A discovery endpoint — returns AgentCard metadata for all registered agents.

    Clients use this to discover which disciplines are available, their skills,
    capabilities, and the item classes each agent handles.
    """
    return {
        "agents": [card.to_dict() for card in AGENT_CARDS.values()],
        "total": len(AGENT_CARDS),
        "protocol": "A2A/1.0",
    }


@app.post("/a2a/orchestrate")
async def a2a_orchestrate(request: A2AOrchestrationRequest):
    """
    Full A2A parallel orchestration endpoint.

    Routes the user query to relevant discipline agents in parallel,
    collects cross-discipline findings via AgentMessageBus, and returns
    a synthesised OrchestratorReport with an executive summary.

    Request body:
    {
        "message": "What are the high-risk topsides and PSV items?",
        "site": "GIR",                    (optional)
        "session_id": "my-session-123",   (optional)
        "disciplines": ["topsides","psv"] (optional, defaults to all)
    }
    """
    try:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="message field is required and cannot be blank")

        logger.info(
            f"A2A orchestrate: site={request.site}, "
            f"disciplines={request.disciplines}, msg_len={len(message)}"
        )

        report = await a2a_orchestrate_fn(
            query=message,
            site=request.site,
            session_id=request.session_id,
            disciplines=request.disciplines,
            model_id=request.model_id,
        )

        # Persist session record
        save_a2a_session({
            "session_id": report.session_id,
            "query": report.query,
            "disciplines_invoked": report.disciplines_invoked,
            "routing_mode": report.routing_mode,
            "executive_summary": report.executive_summary,
            "total_duration_ms": report.total_duration_ms,
            "cross_risks_count": len(report.cross_discipline_risks),
            "ai_used": report.ai_used,
        })

        # Persist individual agent call records
        for disc, resp in report.agent_responses.items():
            log_agent_call({
                "session_id": report.session_id,
                "discipline": disc,
                "agent_name": resp.agent,
                "status": resp.status,
                "kpi_summary": resp.kpi or {},
                "duration_ms": resp.duration_ms,
                "ai_used": resp.ai_used,
            })

        return report.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A2A orchestrate error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


@app.get("/a2a/history")
async def get_a2a_history(limit: int = 20):
    """
    Return recent A2A orchestration session history from the database.

    Query params:
    - limit: max sessions to return (default 20)
    """
    try:
        history = get_a2a_session_history(limit=limit)
        return {"success": True, "sessions": history, "count": len(history)}
    except Exception as e:
        logger.error(f"A2A history error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---- Chat Feedback Endpoints ----
@app.post("/chat/feedback")
async def submit_chat_feedback(feedback: dict):
    """Save thumbs up/down feedback on a chat response."""
    try:
        required = ['message_id', 'query', 'response', 'rating']
        for field in required:
            if field not in feedback:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        if feedback['rating'] not in (-1, 1):
            raise HTTPException(status_code=400, detail="rating must be 1 or -1")

        save_chat_feedback({
            "message_id": str(feedback['message_id']),
            "query": feedback['query'],
            "response": feedback['response'],
            "rating": feedback['rating'],
            "comment": feedback.get('comment'),
            "discipline": feedback.get('discipline'),
            "model_id": feedback.get('model_id'),
            "site": feedback.get('site')
        })
        return {"success": True, "message": "Feedback saved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback save error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/feedback/stats")
async def get_feedback_stats():
    """Return aggregate feedback statistics."""
    try:
        stats = get_chat_feedback_stats()
        return {"success": True, **stats}
    except Exception as e:
        logger.error(f"Feedback stats error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/feedback")
async def list_feedback(rating: Optional[int] = None, limit: int = 50):
    """List recent chat feedback entries."""
    try:
        entries = list_chat_feedback(rating=rating, limit=limit)
        return {"success": True, "feedback": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"Feedback list error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "detail": str(exc)
        }
    )


# ---- Status Management Endpoints ----
@app.get("/items/{tag_id}/status", response_model=StatusHistory)
async def get_status_history_endpoint(tag_id: str):
    """Get status history from database"""
    history_data = get_status_history(tag_id)
    history = [StatusUpdate(**item) for item in history_data]
    return StatusHistory(tag_id=tag_id, history=history)

@app.post("/items/{tag_id}/status", response_model=StatusHistory)
async def add_status_update(tag_id: str, update: StatusUpdate):
    if update.tag_id and update.tag_id != tag_id:
        raise HTTPException(status_code=400, detail="tag_id mismatch between path and body")

    # Save to database
    save_status_update(tag_id, update.new_status, update.note)

    # Also keep in memory for backward compatibility
    new_update = StatusUpdate(tag_id=tag_id, new_status=update.new_status, note=update.note)
    with _status_lock:
        _status_store.setdefault(tag_id, []).append(new_update)

    # Return from database
    history_data = get_status_history(tag_id)
    history = [StatusUpdate(**item) for item in history_data]
    return StatusHistory(tag_id=tag_id, history=history)


# ---- Cache Management Endpoints ----
@app.get("/cache/list")
async def list_cache(site: Optional[str] = None):
    """List all cached files, optionally filtered by site
    
    Args:
        site: Optional site identifier (GIR, DAL, PAZ, CLV) to filter by filename prefix
    """
    try:
        cached_files = list_cached_files(site=site)
        return {"success": True, "files": cached_files}
    except Exception as e:
        logger.error(f"Error listing cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/{file_hash}", response_model=ProcessResponse)
async def load_from_cache(file_hash: str):
    """Load data from cache by file hash"""
    try:
        cached = get_cached_data(file_hash)
        if not cached:
            raise HTTPException(status_code=404, detail="Cache not found for this file hash")

        logger.info(f"Loading from cache: {file_hash[:8]}...")
        raw_items = cached.get("raw_items")
        if raw_items:
            backlog_data = process_backlog_items(raw_items)
            performance_data = process_performance_items(raw_items)
            pending_data = process_pending_items(raw_items)
            items_total = len(raw_items)
        else:
            backlog_data = cached["backlog"]
            performance_data = cached["performance"]
            pending_data = cached.get("pending", [])
            items_total = cached["items_processed"]

        sow_progress_data = cached.get("sow_progress", {})
        if isinstance(sow_progress_data, str):
            import json
            sow_progress_data = json.loads(sow_progress_data)

        return ProcessResponse(
            success=True,
            message=f"Loaded from cache: {items_total} items ({len(backlog_data)} backlog, {len(performance_data)} performance, {len(pending_data)} pending)",
            items_processed=items_total,
            dashboard={
                "backlog": backlog_data,
                "performance": performance_data,
                "pending": pending_data,
                "sow_progress": sow_progress_data
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading from cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---- Equipment Master Data Endpoints (SAP-like) ----
@app.get("/equipment/{tag_id}", response_model=EquipmentDetail)
async def get_equipment_detail(tag_id: str):
    """Get complete equipment detail with history"""
    try:
        equipment = get_equipment(tag_id)
        if not equipment:
            raise HTTPException(status_code=404, detail=f"Equipment {tag_id} not found")
        
        inspection_history = get_inspection_history(tag_id)
        status_history_data = get_status_history(tag_id)
        
        # Convert to models
        equipment_model = EquipmentMaster(**equipment)
        inspection_records = [InspectionRecord(**rec) for rec in inspection_history]
        status_updates = [StatusUpdate(**rec) for rec in status_history_data]
        
        return EquipmentDetail(
            equipment=equipment_model,
            inspection_history=inspection_records,
            status_history=status_updates
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equipment detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/equipment", response_model=EquipmentMaster)
async def create_or_update_equipment(equipment: EquipmentMaster):
    """Create or update equipment master data"""
    try:
        equipment_dict = equipment.dict(exclude_none=True)
        success = save_equipment(equipment_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save equipment")
        
        # Return updated equipment
        updated = get_equipment(equipment.tag_id)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved equipment")
        
        return EquipmentMaster(**updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving equipment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/equipment/{tag_id}/inspection")
async def add_inspection(tag_id: str, inspection: InspectionRecord):
    """Add inspection record to equipment"""
    try:
        # Verify equipment exists
        equipment = get_equipment(tag_id)
        if not equipment:
            raise HTTPException(status_code=404, detail=f"Equipment {tag_id} not found")
        
        inspection_dict = inspection.dict(exclude_none=True)
        inspection_dict['tag_id'] = tag_id
        success = add_inspection_record(inspection_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add inspection record")
        
        return {"success": True, "message": "Inspection record added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding inspection: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Disable reload to prevent infinite loop from file watchers
    # Set reload=True only for active development
    reload_enabled = os.getenv("DEV_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
        log_level="info"
    )
