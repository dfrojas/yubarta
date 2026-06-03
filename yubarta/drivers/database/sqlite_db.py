"""
Database Manager for Yubarta.

Handles all interactions with the SQLite database.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

from configs.config import config

class DatabaseManager:
    """
    Manages database connections and operations.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        """Creates the necessary tables if they don't exist."""
        print(f"Initializing database at {self.db_path}...")
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS remediation_history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    source TEXT NOT NULL,
                    rule_name TEXT DEFAULT 'N/A',
                    status TEXT NOT NULL, -- e.g., FIRING, ALERTING, RESOLVED, FAILED, EXECUTING
                    diagnosis TEXT,
                    remediation_command TEXT,
                    trigger_metrics TEXT, -- Storing the triggering data as a JSON string
                    ai_confidence REAL,
                    notes TEXT,
                    execution_log TEXT
                )
                """
                )
                print("Database initialized successfully.")
        finally:
            conn.close()

    def add_event(self, event_data: Dict[str, Any]) -> int:
        """Adds a new event to the database."""
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO remediation_history (timestamp, source, status, trigger_metrics)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        event_data.get("timestamp"),
                        event_data.get("source"),
                        "FIRING",  # Initial status
                        json.dumps(event_data),
                    ),
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def get_alarms(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Retrieves a list of alarms, optionally filtered by status."""
        conn = self._get_connection()
        try:
            query = "SELECT event_id, rule_name, status, timestamp, diagnosis, remediation_command FROM remediation_history"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status.upper())
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """Retrieves a single event by its ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM remediation_history WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_event(self, event_id: int, updates: Dict[str, Any]):
        """Updates an event with new information (e.g., diagnosis, status)."""
        conn = self._get_connection()
        try:
            with conn:
                fields = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values()) + [event_id]
                query = f"UPDATE remediation_history SET {fields} WHERE event_id = ?"
                conn.execute(query, tuple(values))
        finally:
            conn.close()

# Instantiate a single database manager for the application
db_manager = DatabaseManager(config.DATABASE_PATH)
