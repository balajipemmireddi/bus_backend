"""
Student CRUD endpoints and management dashboard.
Handles getting, updating, and deleting students with cascading delete across devices.

When a student is deleted:
1. Remove from backend database (encodings + metadata)
2. Mark in deletion queue to sync to all Pi devices
3. Pi devices fetch deletion queue and remove from their local roster
"""

import json
import csv
import io
import uuid
import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import get_conn
from schemas import StudentUpdate

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students")
def list_students():
    """
    Get all students in format: {"total": N, "students": [...]}
    (Fixed response format for management dashboard JavaScript)
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    
    students = []
    for r in rows:
        students.append({
            "child_id": r["child_id"],
            "name": r["name"],
            "assigned_bus_id": r["assigned_bus_id"],
            "pickup_stop_id": r["pickup_stop_id"],
            "drop_stop_id": r["drop_stop_id"],
            "twin_group": r["twin_group"],
            "encoding_count": len(json.loads(r["encodings"])),
        })
    
    return {
        "total": len(students),
        "students": students
    }


@router.get("/students/{child_id}")
def get_student_detail(child_id: str):
    """Get details for a specific student."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE child_id=?", (child_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(404, f"Student '{child_id}' not found")
    
    return {
        "child_id": row["child_id"],
        "name": row["name"],
        "assigned_bus_id": row["assigned_bus_id"],
        "pickup_stop_id": row["pickup_stop_id"],
        "drop_stop_id": row["drop_stop_id"],
        "twin_group": row["twin_group"],
        "encoding_count": len(json.loads(row["encodings"])),
    }


@router.post("/students/{child_id}")
def update_student(child_id: str, data: StudentUpdate):
    """Update a student's details."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE child_id=?", (child_id,)).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(404, f"Student '{child_id}' not found")
    
    # Build update query with only non-None fields
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.assigned_bus_id is not None:
        updates["assigned_bus_id"] = data.assigned_bus_id
    if data.pickup_stop_id is not None:
        updates["pickup_stop_id"] = data.pickup_stop_id
    if data.drop_stop_id is not None:
        updates["drop_stop_id"] = data.drop_stop_id
    if data.twin_group is not None:
        updates["twin_group"] = data.twin_group
    
    if updates:
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [child_id]
        conn.execute(f"UPDATE students SET {set_clause} WHERE child_id=?", values)
        conn.commit()
    
    conn.close()
    return {"status": "ok", "message": f"Student '{child_id}' updated"}


@router.delete("/students/{child_id}")
def delete_student(child_id: str):
    """
    Delete a specific student - cascades to all Pi devices.
    
    Process:
    1. Remove student from backend database (encodings deleted)
    2. Queue deletion event for all Pi devices to sync
    3. Returns confirmation with deletion ID for tracking
    """
    conn = get_conn()
    row = conn.execute("SELECT name FROM students WHERE child_id=?", (child_id,)).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(404, f"Student '{child_id}' not found")
    
    name = row["name"]
    
    # Delete from main students table (encodings deleted with it)
    conn.execute("DELETE FROM students WHERE child_id=?", (child_id,))
    
    # Queue deletion event for all Pi devices to remove from their roster
    deletion_uuid = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO deletion_queue (deletion_uuid, child_id, student_name, status, created_at, synced_count)
           VALUES (?, ?, ?, 'pending', ?, 0)""",
        (deletion_uuid, child_id, name, now)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "message": f"Deleted '{name}' ({child_id}) - cascading to all Pi devices",
        "deletion_id": deletion_uuid,
        "student_name": name,
        "child_id": child_id
    }


@router.delete("/students")
def delete_all_students(confirm: str | None = None):
    """
    Delete ALL students - cascades to all Pi devices.
    Requires confirmation query parameter.
    """
    if confirm != "yes-delete-all":
        raise HTTPException(400, "Confirm with ?confirm=yes-delete-all to delete all students")
    
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) as cnt FROM students").fetchone()["cnt"]
    
    # Get all child_ids for deletion queue
    rows = conn.execute("SELECT child_id, name FROM students").fetchall()
    
    # Delete from students
    conn.execute("DELETE FROM students")
    
    # Queue deletion event for each student
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for row in rows:
        deletion_uuid = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO deletion_queue (deletion_uuid, child_id, student_name, status, created_at, synced_count)
               VALUES (?, ?, ?, 'pending', ?, 0)""",
            (deletion_uuid, row["child_id"], row["name"], now)
        )
    
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "message": f"Deleted {count} students - cascading deletions queued for all Pi devices",
        "deleted_count": count
    }


@router.get("/deletion-queue")
def get_deletion_queue():
    """
    Get pending deletions waiting to be synced to Pi devices.
    Pi calls this endpoint to fetch what students it should delete.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM deletion_queue WHERE status='pending' ORDER BY created_at"
    ).fetchall()
    conn.close()
    
    deletions = []
    for r in rows:
        deletions.append({
            "deletion_uuid": r["deletion_uuid"],
            "child_id": r["child_id"],
            "student_name": r["student_name"],
            "created_at": r["created_at"],
        })
    
    return {
        "total": len(deletions),
        "deletions": deletions
    }


@router.post("/deletion-queue/{deletion_uuid}/ack")
def acknowledge_deletion(deletion_uuid: str, bus_id: str):
    """
    Pi acknowledges that it has processed a deletion.
    Tracks which buses have successfully deleted the student.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM deletion_queue WHERE deletion_uuid=?",
        (deletion_uuid,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(404, f"Deletion record not found: {deletion_uuid}")
    
    # Increment synced_count
    new_count = row["synced_count"] + 1
    conn.execute(
        """UPDATE deletion_queue SET synced_count=? WHERE deletion_uuid=?""",
        (new_count, deletion_uuid)
    )
    
    # Mark as completed if all known buses have acknowledged (we assume 2-3 buses typically)
    # This is a simplification - in production you'd track registered buses
    if new_count >= 2:  # Mark complete after 2 buses acknowledge
        conn.execute(
            """UPDATE deletion_queue SET status='completed' WHERE deletion_uuid=?""",
            (deletion_uuid,)
        )
    
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "message": f"Deletion acknowledged by bus {bus_id}",
        "synced_count": new_count
    }


@router.get("/students/export/csv")
def export_students():
    """Export all students as CSV."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT child_id, name, assigned_bus_id, pickup_stop_id, drop_stop_id, twin_group FROM students ORDER BY name"
    ).fetchall()
    conn.close()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Child ID", "Name", "Bus ID", "Pickup Stop", "Drop Stop", "Twin Group"])
    
    for row in rows:
        writer.writerow([
            row["child_id"],
            row["name"],
            row["assigned_bus_id"],
            row["pickup_stop_id"],
            row["drop_stop_id"],
            row["twin_group"] or "",
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"}
    )


@router.get("/students/health")
def students_health():
    """Health check - returns student count and db status."""
    try:
        conn = get_conn()
        count = conn.execute("SELECT COUNT(*) as cnt FROM students").fetchone()["cnt"]
        conn.close()
        return {"status": "ok", "student_count": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
