-- Track A2A agent sessions
CREATE TABLE a2a_sessions (
    session_id TEXT PRIMARY KEY,
    agent_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP
);

-- Track agent calls
CREATE TABLE agent_calls (
    call_id TEXT PRIMARY KEY,
    session_id TEXT,
    agent_name TEXT,
    query TEXT,
    response_hash TEXT,
    duration_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES a2a_sessions(session_id)
);