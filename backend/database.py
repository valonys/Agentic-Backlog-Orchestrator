"""
SQLite database for caching processed Excel data
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

DB_PATH = "backlog_cache.db"

def get_db_connection():
    """Get SQLite connection"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # File cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_cache (
            file_hash TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            processed_at TIMESTAMP NOT NULL,
            total_items INTEGER NOT NULL,
            backlog_count INTEGER NOT NULL,
            performance_count INTEGER NOT NULL,
            sow_progress TEXT NOT NULL,
            raw_data TEXT NOT NULL
        )
    """)
    
    # Status history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id TEXT NOT NULL,
            new_status TEXT NOT NULL,
            note TEXT,
            timestamp TIMESTAMP NOT NULL,
            file_hash TEXT,
            FOREIGN KEY (file_hash) REFERENCES file_cache(file_hash)
        )
    """)
    
    # Equipment master data table (SAP-like)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment_master (
            tag_id TEXT PRIMARY KEY,
            functional_location TEXT,
            equipment_category TEXT,
            description TEXT,
            system TEXT,
            location TEXT,
            manufacturing_details TEXT,
            fluid_service TEXT,
            backlog_tracker TEXT,
            inspections_done TEXT,
            history_comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
    """)
    
    # Inspection history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id TEXT NOT NULL,
            inspection_date TEXT,
            inspection_type TEXT,
            result TEXT,
            inspector TEXT,
            notes TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tag_id) REFERENCES equipment_master(tag_id)
        )
    """)

    # A2A session tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS a2a_sessions (
            session_id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            disciplines_invoked TEXT NOT NULL,
            routing_mode TEXT NOT NULL,
            executive_summary TEXT,
            total_duration_ms INTEGER DEFAULT 0,
            cross_risks_count INTEGER DEFAULT 0,
            ai_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # A2A individual agent call tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_calls (
            call_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            discipline TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            kpi_summary TEXT,
            duration_ms INTEGER DEFAULT 0,
            ai_used INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES a2a_sessions(session_id)
        )
    """)

    # Chat feedback table — thumbs up/down for RLHF-style retraining loop
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
            comment TEXT,
            discipline TEXT,
            model_id TEXT,
            site TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized")

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_cached_data(file_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached data if available"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM file_cache WHERE file_hash = ?",
            (file_hash,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"Cache hit for file hash: {file_hash[:8]}...")
            raw_payload = json.loads(row["raw_data"])
            sow_progress_data = row["sow_progress"]
            if isinstance(sow_progress_data, str):
                sow_progress_data = json.loads(sow_progress_data)
            return {
                "backlog": raw_payload.get("backlog", []),
                "performance": raw_payload.get("performance", []),
                "pending": raw_payload.get("pending", []),
                "raw_items": raw_payload.get("items"),
                "sow_progress": sow_progress_data,
                "items_processed": row["total_items"],
                "backlog_count": row["backlog_count"],
                "performance_count": row["performance_count"]
            }
    except Exception as e:
        logger.warning(f"Error reading cache: {str(e)}")
    return None

def cache_data(
    file_hash: str,
    filename: str,
    backlog_data: List[Dict],
    performance_data: List[Dict],
    pending_data: List[Dict],
    sow_progress: Dict,
    total_items: int,
    raw_items: Optional[List[Dict]] = None
):
    """Cache processed data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        raw_data = json.dumps({
            "items": raw_items,
            "backlog": backlog_data,
            "performance": performance_data,
            "pending": pending_data
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
            total_items,
            len(backlog_data),
            len(performance_data),
            json.dumps(sow_progress),
            raw_data
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Cached data for file hash: {file_hash[:8]}...")
    except Exception as e:
        logger.error(f"Error caching data: {str(e)}")

def save_status_update(tag_id: str, new_status: str, note: Optional[str], file_hash: Optional[str] = None):
    """Save status update to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO status_history (tag_id, new_status, note, timestamp, file_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (tag_id, new_status, note or "", datetime.now().isoformat(), file_hash))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving status update: {str(e)}")

def get_status_history(tag_id: str) -> List[Dict]:
    """Get status history for a tag"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT new_status, note, timestamp 
            FROM status_history 
            WHERE tag_id = ? 
            ORDER BY timestamp DESC
        """, (tag_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "tag_id": tag_id,
                "new_status": row["new_status"],
                "note": row["note"],
                "timestamp": row["timestamp"]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error getting status history: {str(e)}")
        return []

def list_cached_files(site: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all cached files, optionally filtered by site identifier
    
    Args:
        site: Optional site identifier (GIR, DAL, PAZ, CLV) to filter by filename prefix
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if site:
            # Filter by site - filename should start with site identifier
            site_upper = site.upper()
            cursor.execute("""
                SELECT file_hash, filename, processed_at, total_items,
                       backlog_count, performance_count
                FROM file_cache
                WHERE UPPER(SUBSTR(filename, 1, 3)) = ?
                ORDER BY processed_at DESC
                LIMIT 10
            """, (site_upper,))
        else:
            cursor.execute("""
                SELECT file_hash, filename, processed_at, total_items,
                       backlog_count, performance_count
                FROM file_cache
                ORDER BY processed_at DESC
                LIMIT 10
            """)
        
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "file_hash": row["file_hash"],
                "filename": row["filename"],
                "processed_at": row["processed_at"],
                "total_items": row["total_items"],
                "backlog_count": row["backlog_count"],
                "performance_count": row["performance_count"]
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error listing cached files: {str(e)}")
        return []

def get_equipment(tag_id: str) -> Optional[Dict[str, Any]]:
    """Get equipment master data by tag_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM equipment_master WHERE tag_id = ?",
            (tag_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Error getting equipment: {str(e)}")
        return None

def save_equipment(equipment_data: Dict[str, Any]) -> bool:
    """Save or update equipment master data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if exists
        existing = get_equipment(equipment_data['tag_id'])
        
        if existing:
            # Update
            cursor.execute("""
                UPDATE equipment_master SET
                    functional_location = ?,
                    equipment_category = ?,
                    description = ?,
                    system = ?,
                    location = ?,
                    manufacturing_details = ?,
                    fluid_service = ?,
                    backlog_tracker = ?,
                    inspections_done = ?,
                    history_comments = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE tag_id = ?
            """, (
                equipment_data.get('functional_location'),
                equipment_data.get('equipment_category'),
                equipment_data.get('description'),
                equipment_data.get('system'),
                equipment_data.get('location'),
                equipment_data.get('manufacturing_details'),
                equipment_data.get('fluid_service'),
                equipment_data.get('backlog_tracker'),
                equipment_data.get('inspections_done'),
                equipment_data.get('history_comments'),
                equipment_data.get('updated_by', 'system'),
                equipment_data['tag_id']
            ))
        else:
            # Insert
            cursor.execute("""
                INSERT INTO equipment_master 
                (tag_id, functional_location, equipment_category, description,
                 system, location, manufacturing_details, fluid_service,
                 backlog_tracker, inspections_done, history_comments, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                equipment_data['tag_id'],
                equipment_data.get('functional_location'),
                equipment_data.get('equipment_category'),
                equipment_data.get('description'),
                equipment_data.get('system'),
                equipment_data.get('location'),
                equipment_data.get('manufacturing_details'),
                equipment_data.get('fluid_service'),
                equipment_data.get('backlog_tracker'),
                equipment_data.get('inspections_done'),
                equipment_data.get('history_comments'),
                equipment_data.get('created_by', 'system')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved equipment: {equipment_data['tag_id']}")
        return True
    except Exception as e:
        logger.error(f"Error saving equipment: {str(e)}")
        return False

def get_inspection_history(tag_id: str) -> List[Dict[str, Any]]:
    """Get inspection history for equipment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM inspection_history 
            WHERE tag_id = ? 
            ORDER BY inspection_date DESC, timestamp DESC
        """, (tag_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error getting inspection history: {str(e)}")
        return []

def add_inspection_record(inspection_data: Dict[str, Any]) -> bool:
    """Add inspection record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inspection_history
            (tag_id, inspection_date, inspection_type, result, inspector, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            inspection_data['tag_id'],
            inspection_data.get('inspection_date'),
            inspection_data.get('inspection_type'),
            inspection_data.get('result'),
            inspection_data.get('inspector'),
            inspection_data.get('notes')
        ))
        conn.commit()
        conn.close()
        logger.info(f"Added inspection record for: {inspection_data['tag_id']}")
        return True
    except Exception as e:
        logger.error(f"Error adding inspection record: {str(e)}")
        return False


# ---------------------------------------------------------------------------
# A2A session / agent-call persistence
# ---------------------------------------------------------------------------

def save_a2a_session(session_data: Dict[str, Any]) -> bool:
    """Persist an A2A orchestration session record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO a2a_sessions
            (session_id, query, disciplines_invoked, routing_mode,
             executive_summary, total_duration_ms, cross_risks_count, ai_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_data["session_id"],
            session_data.get("query", ""),
            json.dumps(session_data.get("disciplines_invoked", [])),
            session_data.get("routing_mode", "multi"),
            session_data.get("executive_summary", ""),
            session_data.get("total_duration_ms", 0),
            session_data.get("cross_risks_count", 0),
            1 if session_data.get("ai_used") else 0,
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error(f"Error saving A2A session: {exc}")
        return False


def log_agent_call(call_data: Dict[str, Any]) -> bool:
    """Log a single discipline agent call within an A2A session."""
    import uuid as _uuid
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO agent_calls
            (call_id, session_id, discipline, agent_name, status,
             kpi_summary, duration_ms, ai_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            call_data.get("call_id", str(_uuid.uuid4())),
            call_data["session_id"],
            call_data.get("discipline", ""),
            call_data.get("agent_name", ""),
            call_data.get("status", "completed"),
            json.dumps(call_data.get("kpi_summary", {})),
            call_data.get("duration_ms", 0),
            1 if call_data.get("ai_used") else 0,
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error(f"Error logging agent call: {exc}")
        return False


def get_a2a_session_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return recent A2A orchestration sessions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, query, disciplines_invoked, routing_mode,
                   total_duration_ms, cross_risks_count, ai_used, created_at
            FROM a2a_sessions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["disciplines_invoked"] = json.loads(d["disciplines_invoked"])
            except Exception:
                pass
            result.append(d)
        return result
    except Exception as exc:
        logger.error(f"Error fetching A2A session history: {exc}")
        return []

# ---------------------------------------------------------------------------
# Chat feedback persistence (thumbs up/down → retraining loop)
# ---------------------------------------------------------------------------

def save_chat_feedback(feedback: Dict[str, Any]) -> bool:
    """Save a thumbs-up / thumbs-down rating for a chat response."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_feedback
            (message_id, query, response, rating, comment, discipline, model_id, site)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback["message_id"],
            feedback.get("query", ""),
            feedback.get("response", ""),
            feedback["rating"],              # 1 = thumbs up, -1 = thumbs down
            feedback.get("comment", ""),
            feedback.get("discipline"),
            feedback.get("model_id"),
            feedback.get("site"),
        ))
        conn.commit()
        conn.close()
        logger.info(f"Saved chat feedback: msg={feedback['message_id']}, rating={feedback['rating']}")
        return True
    except Exception as exc:
        logger.error(f"Error saving chat feedback: {exc}")
        return False


def get_chat_feedback_stats() -> Dict[str, Any]:
    """Return aggregate feedback statistics for monitoring."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS thumbs_up,
                SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS thumbs_down
            FROM chat_feedback
        """)
        row = cursor.fetchone()
        conn.close()
        if row:
            total = row["total"] or 0
            up = row["thumbs_up"] or 0
            down = row["thumbs_down"] or 0
            return {
                "total": total,
                "thumbs_up": up,
                "thumbs_down": down,
                "approval_rate": round(up / total * 100, 1) if total > 0 else 0.0,
            }
        return {"total": 0, "thumbs_up": 0, "thumbs_down": 0, "approval_rate": 0.0}
    except Exception as exc:
        logger.error(f"Error fetching feedback stats: {exc}")
        return {"total": 0, "thumbs_up": 0, "thumbs_down": 0, "approval_rate": 0.0}


def list_chat_feedback(limit: int = 50, rating: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return recent feedback entries, optionally filtered by rating (-1 or 1)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if rating is not None:
            cursor.execute("""
                SELECT * FROM chat_feedback
                WHERE rating = ?
                ORDER BY created_at DESC LIMIT ?
            """, (rating, limit))
        else:
            cursor.execute("""
                SELECT * FROM chat_feedback
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error(f"Error listing chat feedback: {exc}")
        return []


# Initialize on import
init_db()
