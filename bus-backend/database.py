"""
Database initialization and connection helpers.
Centralizes SQLite schema and connection management.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "backend.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    """Get a new database connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            child_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            encodings TEXT NOT NULL,
            assigned_bus_id TEXT,
            pickup_stop_id TEXT,
            drop_stop_id TEXT,
            twin_group TEXT
        );

        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL,
            radius_m REAL DEFAULT 125
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id TEXT,
            event_type TEXT NOT NULL,
            confidence REAL,
            photo_path TEXT,
            gps_lat REAL,
            gps_lng REAL,
            bus_id TEXT,
            timestamp TEXT NOT NULL,
            review_status TEXT DEFAULT 'n/a'  -- n/a | pending | confirmed | rejected
        );

        CREATE TABLE IF NOT EXISTS devices (
            bus_id TEXT PRIMARY KEY,
            last_heartbeat TEXT,
            status TEXT DEFAULT 'offline'  -- online | offline
        );

        CREATE TABLE IF NOT EXISTS enrollment_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id TEXT,
            name TEXT,
            bus_id TEXT,
            pickup_stop_id TEXT,
            drop_stop_id TEXT,
            twin_group TEXT,
            photos TEXT,  -- JSON list of base64 encoded photos
            status TEXT DEFAULT 'processing',  -- processing | completed | failed
            encodings TEXT,  -- JSON list of successful encodings
            error_msg TEXT,
            created_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()
