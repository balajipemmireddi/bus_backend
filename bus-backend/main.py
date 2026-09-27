"""
Minimal cloud backend - built for speed to get an end-to-end demo working fast.

Uses SQLite (not Postgres) deliberately, to skip DB server setup while racing a
deadline. Per the main spec (§4), swap to Postgres before real multi-bus production
use - SQLite's single-writer lock will bottleneck once several buses sync
concurrently. Swapping later just means changing the SQLAlchemy connection string;
the schema/queries below are written in plain-enough SQL to port easily.

Run:
    pip install fastapi uvicorn --break-system-packages
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /api/enroll                    - add/update a student + encodings
    GET  /api/bus/{bus_id}/roster        - full roster sync (every device gets everything, §12)
    POST /api/events                     - edge devices push queued events here
    GET  /api/review                     - list pending review-queue items
    POST /api/review/{event_id}/resolve  - staff confirms/rejects a review item
    GET  /api/live                       - latest event per bus, for the live feed (§10)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import json
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "backend.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Bus Pickup/Drop Backend (dev)")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
        """
    )
    conn.commit()
    conn.close()


init_db()


# ---- Schemas ----

class StudentIn(BaseModel):
    child_id: str
    name: str
    encodings: list[list[float]]
    assigned_bus_id: str
    pickup_stop_id: str
    drop_stop_id: str
    twin_group: str | None = None


class EventIn(BaseModel):
    child_id: str
    event_type: str          # PICKED_UP | DROPPED | EXIT_UNEXPECTED_LOCATION | UNMATCHED_REVIEW
    confidence: float
    photo_path: str | None = ""
    gps_lat: float | None = None
    gps_lng: float | None = None
    bus_id: str
    timestamp: str | None = None


# ---- Enrollment ----

@app.post("/api/enroll")
def enroll(student: StudentIn):
    conn = get_conn()
    conn.execute(
        """INSERT INTO students (child_id, name, encodings, assigned_bus_id, pickup_stop_id, drop_stop_id, twin_group)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(child_id) DO UPDATE SET
             name=excluded.name, encodings=excluded.encodings,
             assigned_bus_id=excluded.assigned_bus_id,
             pickup_stop_id=excluded.pickup_stop_id, drop_stop_id=excluded.drop_stop_id,
             twin_group=excluded.twin_group""",
        (student.child_id, student.name, json.dumps(student.encodings),
         student.assigned_bus_id, student.pickup_stop_id, student.drop_stop_id, student.twin_group),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "child_id": student.child_id}


# ---- Roster sync (§12: full roster to every device) ----

@app.get("/api/bus/{bus_id}/roster")
def get_roster(bus_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return [
        {
            "child_id": r["child_id"],
            "name": r["name"],
            "encodings": json.loads(r["encodings"]),
            "assigned_bus_id": r["assigned_bus_id"],
            "pickup_stop_id": r["pickup_stop_id"],
            "drop_stop_id": r["drop_stop_id"],
            "twin_group": r["twin_group"],
        }
        for r in rows
    ]


# ---- Event ingest (from edge devices via sync_client.py) ----

@app.post("/api/events")
def ingest_event(event: EventIn):
    conn = get_conn()
    review_status = "pending" if event.event_type == "UNMATCHED_REVIEW" else "n/a"
    ts = event.timestamp or datetime.datetime.now().isoformat()
    cur = conn.execute(
        """INSERT INTO events (child_id, event_type, confidence, photo_path, gps_lat, gps_lng, bus_id, timestamp, review_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event.child_id, event.event_type, event.confidence, event.photo_path,
         event.gps_lat, event.gps_lng, event.bus_id, ts, review_status),
    )
    conn.commit()
    event_id = cur.lastrowid
    conn.close()

    # In production: trigger the WhatsApp send here for PICKED_UP/DROPPED (§9, Phase 6 - not built yet)
    if event.event_type in ("PICKED_UP", "DROPPED"):
        print(f"[WOULD SEND WHATSAPP] {event.event_type} for {event.child_id} on {event.bus_id}")

    return {"status": "ok", "event_id": event_id}


# ---- Review queue (§9) ----

@app.get("/api/review")
def list_review_queue():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM events WHERE review_status='pending'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/review/{event_id}/resolve")
def resolve_review(event_id: int, decision: str, confirmed_child_id: str | None = None):
    if decision not in ("confirmed", "rejected"):
        raise HTTPException(400, "decision must be 'confirmed' or 'rejected'")
    conn = get_conn()
    if decision == "confirmed" and confirmed_child_id:
        conn.execute(
            "UPDATE events SET review_status=?, child_id=? WHERE id=?",
            (decision, confirmed_child_id, event_id),
        )
    else:
        conn.execute("UPDATE events SET review_status=? WHERE id=?", (decision, event_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ---- Live feed (§10 - always-on event feed) ----

@app.get("/api/live")
def live_feed(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/")
def root():
    return {"status": "Bus backend running", "docs": "/docs"}
