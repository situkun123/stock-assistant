import json
import os
import sqlite3
from pathlib import Path

import duckdb

root_dir = Path(__file__).resolve().parent.parent


class Logger:
    def __init__(self, database_name: str, token: str = None):
        """Initialize Logger with database connection details."""
        try:
            self.token = token or os.getenv("DUCK_DB_TOKEN")
            if not self.token:
                raise ValueError("MotherDuck token not provided and DUCK_DB_TOKEN environment variable not set")

            self.database_name = database_name
            self.conn_str = f"md:{database_name}?motherduck_token={self.token}"
            self.conn = None
            self.max_length = 1000  # Max length for query and response to prevent oversized entries
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Logger: {e}")

    def connect(self):
        """Establish connection to MotherDuck database."""
        try:
            if not self.conn:
                self.conn = duckdb.connect(self.conn_str)
                self._ensure_table_exists()
                print(f"✓ Connected to MotherDuck database: {self.database_name}")
            return self
        except duckdb.ConnectionException as e:
            raise ConnectionError(f"Failed to connect to MotherDuck: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during connection: {e}")

    def _ensure_table_exists(self):
        """Creates the audit log table with nested types for tools."""
        create_query = """
        CREATE TABLE IF NOT EXISTS agent_logs (
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            query TEXT,
            response TEXT,
            total_tokens INTEGER,
            total_cost_usd DOUBLE,
            tool_calls INTEGER,
            tools_used JSON,
            model_name VARCHAR DEFAULT 'gpt-4o-mini'
        )
        """
        try:
            self.conn.execute(create_query)
            print("✓ Table 'agent_runs' is ready")
        except Exception as e:
            raise RuntimeError(f"Unexpected error creating table: {e}")

    def _truncate_text(self, text: str, max_length: int = None) -> str:
        """Truncate text to maximum length with ellipsis."""
        if max_length is None:
            max_length = self.max_length

        if len(text) <= max_length:
            return text

        return text[:max_length - 3] + "..."

    def log_agent_run(self, query: str, response: str, metadata: dict):
        """Inserts agent execution data into MotherDuck."""
        if not self.conn:
            self.connect()

        # Convert tools list to JSON string for storage
        tools_json = json.dumps(metadata.get("tools_used", []))

        # Truncate query and response
        truncated_query = self._truncate_text(query)
        truncated_response = self._truncate_text(response)

        # Log if truncation occurred
        if len(query) > self.max_length:
            print(f"ℹ️  Query truncated from {len(query)} to {self.max_length} characters")
        if len(response) > self.max_length:
            print(f"ℹ️  Response truncated from {len(response)} to {self.max_length} characters")
        insert_query = """
        INSERT INTO agent_logs (query, response, total_tokens, total_cost_usd, tool_calls, tools_used)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(insert_query, (
            truncated_query,
            truncated_response,
            metadata['total_tokens'],
            metadata['total_cost_usd'],
            metadata['tool_calls'],
            tools_json
        ))
        print("Successfully logged run to MotherDuck.")

    def close(self):
        if self.conn:
            self.conn.close()


def clear_thread_checkpoints(thread_id: str):
    """Clear checkpoints for a specific thread."""
    db_path = os.getenv("CHECKPOINT_DB_PATH", str(root_dir / "data" / "checkpoints.db"))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table exists before attempting delete
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='checkpoints'
    """)
    
    if cursor.fetchone() is None:
        print(f"⚠️  Checkpoints table doesn't exist yet — nothing to clear.")
        conn.close()
        return

    cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close()
