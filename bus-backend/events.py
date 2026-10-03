"""
Event endpoints - ingestion and review queue for edge device events.

Uses new normalized schema:
- attendance_events: PICKED_UP, DROPPED, etc.
- review_cases: UNMATCHED, AMBIGUOUS detections

Phase 1: Events flow directly to attendance_events.
Phase 2+: Can add approval workflow.
"""

import datetime
import uuid
from fastapi import APIRouter, HTTPException

from database import get_conn
from schemas import AttendanceEventIn, ReviewCaseResponse

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/events")
def ingest_event(event: AttendanceEventIn):
    """
    Event ingestion from edge devices via sync_client.py.
    Creates attendance event and optional review case for ambiguous/unmatched.
    """
    conn = get_conn()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        event_uuid = event.event_uuid or str(uuid.uuid4())
        event_timestamp = event.timestamp or now
        
        # Validate student exists if student_id is provided
        if event.student_id:
            student = conn.execute(
                "SELECT id FROM students WHERE id=?",
                (event.student_id,)
            ).fetchone()
            if not student:
                conn.close()
                raise HTTPException(404, f"Student ID {event.student_id} not found")
        
        # Validate bus exists
        bus = conn.execute(
            "SELECT id FROM buses WHERE id=?",
            (event.bus_id,)
        ).fetchone()
        if not bus:
            conn.close()
            raise HTTPException(404, f"Bus ID {event.bus_id} not found")
        
        # Insert attendance event
        cursor = conn.execute(
            """INSERT INTO attendance_events
               (event_uuid, student_id, bus_id, event_type, timestamp, confidence, 
                direction, latitude, longitude, photo_path, source_device, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_uuid, event.student_id, event.bus_id, event.event_type,
             event_timestamp, event.confidence, event.direction,
             event.latitude, event.longitude, event.photo_path, event.source_device, now)
        )
        event_id = cursor.lastrowid
        
        # Create review case for ambiguous/unmatched events
        if event.event_type in ("UNMATCHED_REVIEW", "AMBIGUOUS_REVIEW"):
            case_type = "UNMATCHED" if event.event_type == "UNMATCHED_REVIEW" else "AMBIGUOUS"
            conn.execute(
                """INSERT INTO review_cases
                   (event_uuid, student_id, bus_id, case_type, confidence, evidence_path, 
                    status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_uuid, event.student_id, event.bus_id, case_type,
                 event.confidence, event.photo_path, "pending", now)
            )
        
        conn.commit()
        
        return {
            "status": "ok",
            "event_id": event_id,
            "event_uuid": event_uuid,
            "event_type": event.event_type
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Failed to ingest event: {str(e)}")
    finally:
        conn.close()


@router.get("/review")
def list_review_queue(status: str = "pending", limit: int = 50):
    """
    List review queue items (unmatched/ambiguous detections).
    """
    conn = get_conn()
    
    rows = conn.execute(
        """SELECT * FROM review_cases 
           WHERE status=?
           ORDER BY created_at DESC
           LIMIT ?""",
        (status, limit)
    ).fetchall()
    
    conn.close()
    
    return {
        "total": len(rows),
        "status": status,
        "cases": [dict(r) for r in rows]
    }


@router.post("/review/{case_id}/resolve")
def resolve_review_case(case_id: int, decision: str, confirmed_student_id: int | None = None, resolution_notes: str | None = None):
    """
    Resolve a review case: confirmed (match found) or rejected (false detection).
    """
    if decision not in ("confirmed", "rejected"):
        raise HTTPException(400, "decision must be 'confirmed' or 'rejected'")
    
    conn = get_conn()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        
        # Get the review case
        case = conn.execute(
            "SELECT * FROM review_cases WHERE id=?",
            (case_id,)
        ).fetchone()
        
        if not case:
            conn.close()
            raise HTTPException(404, f"Review case {case_id} not found")
        
        # If confirmed with new student ID, update the original event
        if decision == "confirmed" and confirmed_student_id is not None:
            conn.execute(
                """UPDATE attendance_events 
                   SET student_id=? 
                   WHERE event_uuid=?""",
                (confirmed_student_id, case["event_uuid"])
            )
            student_id = confirmed_student_id
        else:
            student_id = case["student_id"]
        
        # Update review case
        conn.execute(
            """UPDATE review_cases 
               SET status=?, student_id=?, resolved_at=?, resolution=?
               WHERE id=?""",
            (decision, student_id, now, resolution_notes, case_id)
        )
        
        conn.commit()
        
        return {
            "status": "ok",
            "case_id": case_id,
            "resolution": decision,
            "confirmed_student_id": student_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Failed to resolve review case: {str(e)}")
    finally:
        conn.close()


@router.get("/live")
def live_feed(limit: int = 50):
    """
    Latest events for live dashboard feed.
    Returns recent attendance events.
    """
    conn = get_conn()
    
    rows = conn.execute(
        """SELECT 
             ae.id, ae.event_uuid, ae.student_id, ae.bus_id, ae.event_type,
             ae.timestamp, ae.confidence, ae.direction, ae.latitude, ae.longitude,
             ae.photo_path, ae.source_device, ae.created_at,
             s.admission_number, s.first_name, s.last_name,
             b.code as bus_code
           FROM attendance_events ae
           LEFT JOIN students s ON s.id = ae.student_id
           LEFT JOIN buses b ON b.id = ae.bus_id
           ORDER BY ae.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    conn.close()
    
    events = []
    for r in rows:
        events.append({
            "id": r[0],
            "event_uuid": r[1],
            "student_id": r[2],
            "bus_id": r[3],
            "event_type": r[4],
            "timestamp": r[5],
            "confidence": r[6],
            "direction": r[7],
            "latitude": r[8],
            "longitude": r[9],
            "photo_path": r[10],
            "source_device": r[11],
            "created_at": r[12],
            "student_name": f"{r[14]} {r[15]}" if r[13] else "Unknown",
            "admission_number": r[13],
            "bus_code": r[17],
        })
    
    return events
