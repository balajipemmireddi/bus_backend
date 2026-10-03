"""
Event endpoints - ingestion and review queue for edge device events.
"""

import datetime
import uuid
from fastapi import APIRouter, HTTPException

from database import get_conn
from schemas import EventIn

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/events")
def ingest_event(event: EventIn):
    """
    Event ingestion from edge devices via sync_client.py.
    Events are queued for later review or processed automatically.
    """
    conn = get_conn()
    # Mark UNMATCHED_REVIEW and AMBIGUOUS_REVIEW as pending for manual review
    review_status = "pending" if event.event_type in ("UNMATCHED_REVIEW", "AMBIGUOUS_REVIEW") else "n/a"
    ts = event.timestamp or datetime.datetime.now().isoformat()
    event_uuid = event.event_uuid or str(uuid.uuid4())
    
    cur = conn.execute(
        """INSERT OR IGNORE INTO events
           (event_uuid, child_id, event_type, confidence, photo_path, gps_lat, gps_lng, bus_id, timestamp, review_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_uuid, event.child_id, event.event_type, event.confidence, event.photo_path,
         event.gps_lat, event.gps_lng, event.bus_id, ts, review_status),
    )
    conn.commit()
    inserted = cur.rowcount == 1
    row = conn.execute("SELECT id FROM events WHERE event_uuid=?", (event_uuid,)).fetchone()
    event_id = row["id"]
    conn.close()

    # In production: trigger WhatsApp send for PICKED_UP/DROPPED (Phase 6 - not built yet)
    if inserted and event.event_type in ("PICKED_UP", "DROPPED"):
        print(f"[WOULD SEND WHATSAPP] {event.event_type} for {event.child_id} on {event.bus_id}")

    return {"status": "ok", "event_id": event_id, "duplicate": not inserted}


@router.get("/review")
def list_review_queue():
    """List pending review queue items (unmatched detections, etc)."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM events WHERE review_status='pending'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/review/{event_id}/resolve")
def resolve_review(event_id: int, decision: str, confirmed_child_id: str | None = None):
    """Resolve a review queue item (confirm or reject)."""
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


@router.get("/live")
def live_feed(limit: int = 50):
    """Latest events for live feed (§10)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
