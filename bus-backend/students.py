"""
Student management endpoints using the new normalized schema.

Endpoints:
- GET /api/students - list all students (with pagination/search)
- GET /api/students/{id} - get student details with guardians and transport
- PUT /api/students/{id} - update student info
- DELETE /api/students/{id} - delete student (cascades to all Pi devices)
- DELETE /api/students - delete all (requires confirmation)
- GET /api/students/export/csv - export to CSV
"""

import json
import csv
import io
import uuid
import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import get_conn
from schemas import StudentUpdate, StudentResponse, StudentDetailResponse

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students")
def list_students(page: int = 1, page_size: int = 20, search: str | None = None, status: str = "active"):
    """
    List students with pagination and optional search.
    Returns total count and paginated results.
    """
    conn = get_conn()
    
    # Build query
    query = "SELECT id, school_id, admission_number, first_name, last_name, class_name, status FROM students WHERE status=?"
    params = [status]
    
    if search:
        query += " AND (first_name LIKE ? OR last_name LIKE ? OR admission_number LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    # Get total count
    count_query = query.replace("SELECT id, school_id, admission_number, first_name, last_name, class_name, status", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]
    
    # Get paginated results
    offset = (page - 1) * page_size
    query += " ORDER BY first_name, last_name LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    students = []
    for r in rows:
        students.append({
            "id": r[0],
            "admission_number": r[2],
            "first_name": r[3],
            "last_name": r[4],
            "class_name": r[5],
            "status": r[6],
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "students": students
    }


@router.get("/students/{student_id}")
def get_student_detail(student_id: int):
    """Get complete student details including guardians, transport, and face profile."""
    conn = get_conn()
    
    # Get student
    student = conn.execute(
        """SELECT id, school_id, admission_number, first_name, last_name, 
                  date_of_birth, class_name, section, profile_photo, gender, status, created_at, updated_at
           FROM students WHERE id=?""",
        (student_id,)
    ).fetchone()
    
    if not student:
        conn.close()
        raise HTTPException(404, f"Student {student_id} not found")
    
    # Get guardians
    guardians = conn.execute(
        """SELECT id, name, relationship, phone, email, is_primary
           FROM guardians WHERE student_id=?
           ORDER BY is_primary DESC, name""",
        (student_id,)
    ).fetchall()
    
    # Get current transport assignment
    transport = conn.execute(
        """SELECT ta.id, ta.bus_id, ta.route_id, ta.pickup_stop_id, ta.drop_stop_id,
                  ta.valid_from, ta.valid_until, ta.morning_enabled, ta.afternoon_enabled, ta.status,
                  b.code as bus_code, r.code as route_code, ps.name as pickup_stop_name, ds.name as drop_stop_name
           FROM transport_assignments ta
           LEFT JOIN buses b ON b.id = ta.bus_id
           LEFT JOIN routes r ON r.id = ta.route_id
           LEFT JOIN stops ps ON ps.id = ta.pickup_stop_id
           LEFT JOIN stops ds ON ds.id = ta.drop_stop_id
           WHERE ta.student_id=? AND ta.status='active'
           ORDER BY ta.valid_from DESC
           LIMIT 1""",
        (student_id,)
    ).fetchone()
    
    # Get face profile
    face_profile = conn.execute(
        """SELECT id, status, encoding_count, quality_score, enrolled_at
           FROM face_profiles WHERE student_id=?""",
        (student_id,)
    ).fetchone()
    
    conn.close()
    
    return {
        "id": student[0],
        "admission_number": student[2],
        "first_name": student[3],
        "last_name": student[4],
        "date_of_birth": student[5],
        "class_name": student[6],
        "section": student[7],
        "profile_photo": student[8],
        "gender": student[9],
        "status": student[10],
        "created_at": student[11],
        "updated_at": student[12],
        "guardians": [
            {
                "id": g[0],
                "name": g[1],
                "relationship": g[2],
                "phone": g[3],
                "email": g[4],
                "is_primary": bool(g[5])
            } for g in guardians
        ],
        "current_transport": {
            "id": transport[0],
            "bus_id": transport[1],
            "bus_code": transport[10],
            "route_id": transport[2],
            "route_code": transport[11],
            "pickup_stop_id": transport[3],
            "pickup_stop_name": transport[12],
            "drop_stop_id": transport[4],
            "drop_stop_name": transport[13],
            "valid_from": transport[5],
            "valid_until": transport[6],
            "morning_enabled": bool(transport[7]),
            "afternoon_enabled": bool(transport[8]),
            "status": transport[9]
        } if transport else None,
        "face_profile": {
            "id": face_profile[0],
            "status": face_profile[1],
            "encoding_count": face_profile[2],
            "quality_score": face_profile[3],
            "enrolled_at": face_profile[4]
        } if face_profile else None,
    }


@router.put("/students/{student_id}")
def update_student(student_id: int, data: StudentUpdate):
    """Update student basic information."""
    conn = get_conn()
    
    # Check student exists
    student = conn.execute("SELECT id FROM students WHERE id=?", (student_id,)).fetchone()
    if not student:
        conn.close()
        raise HTTPException(404, f"Student {student_id} not found")
    
    # Build update query
    updates = {}
    if data.first_name is not None:
        updates["first_name"] = data.first_name
    if data.last_name is not None:
        updates["last_name"] = data.last_name
    if data.date_of_birth is not None:
        updates["date_of_birth"] = data.date_of_birth
    if data.class_name is not None:
        updates["class_name"] = data.class_name
    if data.section is not None:
        updates["section"] = data.section
    if data.profile_photo is not None:
        updates["profile_photo"] = data.profile_photo
    if data.gender is not None:
        updates["gender"] = data.gender
    if data.status is not None:
        updates["status"] = data.status
    
    if updates:
        updates["updated_at"] = datetime.datetime.utcnow().isoformat()
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [student_id]
        conn.execute(f"UPDATE students SET {set_clause} WHERE id=?", values)
        conn.commit()
    
    conn.close()
    return {"status": "ok", "student_id": student_id, "message": "Student updated"}


@router.delete("/students/{student_id}")
def delete_student(student_id: int):
    """
    Delete a student - cascades to all Pi devices via deletion queue.
    Removes student profile, face encodings, and transport assignments.
    """
    conn = get_conn()
    
    # Get student
    student = conn.execute(
        "SELECT admission_number, first_name, last_name FROM students WHERE id=?",
        (student_id,)
    ).fetchone()
    
    if not student:
        conn.close()
        raise HTTPException(404, f"Student {student_id} not found")
    
    try:
        # Delete face encodings
        conn.execute(
            """DELETE FROM face_encodings WHERE face_profile_id IN 
               (SELECT id FROM face_profiles WHERE student_id=?)""",
            (student_id,)
        )
        
        # Delete face profile
        conn.execute("DELETE FROM face_profiles WHERE student_id=?", (student_id,))
        
        # Delete transport assignments
        conn.execute("DELETE FROM transport_assignments WHERE student_id=?", (student_id,))
        
        # Delete guardians
        conn.execute("DELETE FROM guardians WHERE student_id=?", (student_id,))
        
        # Delete student
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        
        # Queue deletion for Pi devices
        deletion_uuid = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        student_name = f"{student[1]} {student[2]}"
        
        conn.execute(
            """INSERT INTO deletion_queue (deletion_uuid, child_id, student_name, status, created_at, synced_count)
               VALUES (?, ?, ?, 'pending', ?, 0)""",
            (deletion_uuid, student[0], student_name, now)
        )
        
        conn.commit()
        
        return {
            "status": "ok",
            "message": f"Deleted {student_name} - cascading to all Pi devices",
            "deletion_id": deletion_uuid,
            "student_id": student_id
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/students")
def delete_all_students(confirm: str | None = None):
    """Delete ALL students - requires confirmation."""
    if confirm != "yes-delete-all":
        raise HTTPException(400, "Confirm with ?confirm=yes-delete-all to delete all students")
    
    conn = get_conn()
    
    try:
        # Get all students
        students = conn.execute("SELECT id, admission_number, first_name, last_name FROM students").fetchall()
        
        if not students:
            conn.close()
            return {"status": "ok", "message": "No students to delete", "deleted_count": 0}
        
        # Delete all encodings
        conn.execute("DELETE FROM face_encodings")
        
        # Delete all face profiles
        conn.execute("DELETE FROM face_profiles")
        
        # Delete all transport assignments
        conn.execute("DELETE FROM transport_assignments")
        
        # Delete all guardians
        conn.execute("DELETE FROM guardians")
        
        # Delete all students
        conn.execute("DELETE FROM students")
        
        # Queue deletions for Pi devices
        now = datetime.datetime.utcnow().isoformat()
        for student in students:
            deletion_uuid = str(uuid.uuid4())
            student_name = f"{student[2]} {student[3]}"
            conn.execute(
                """INSERT INTO deletion_queue (deletion_uuid, child_id, student_name, status, created_at, synced_count)
                   VALUES (?, ?, ?, 'pending', ?, 0)""",
                (deletion_uuid, student[1], student_name, now)
            )
        
        conn.commit()
        
        return {
            "status": "ok",
            "message": f"Deleted all {len(students)} students - cascading to Pi devices",
            "deleted_count": len(students)
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Bulk delete failed: {str(e)}")
    finally:
        conn.close()


@router.get("/students/export/csv")
def export_students():
    """Export all active students as CSV."""
    conn = get_conn()
    
    rows = conn.execute(
        """SELECT s.id, s.admission_number, s.first_name, s.last_name, s.class_name, s.section,
                  ta.bus_id, ta.pickup_stop_id, ta.drop_stop_id,
                  b.code as bus_code, ps.name as pickup_stop, ds.name as drop_stop
           FROM students s
           LEFT JOIN transport_assignments ta ON ta.student_id = s.id AND ta.status = 'active'
           LEFT JOIN buses b ON b.id = ta.bus_id
           LEFT JOIN stops ps ON ps.id = ta.pickup_stop_id
           LEFT JOIN stops ds ON ds.id = ta.drop_stop_id
           WHERE s.status = 'active'
           ORDER BY s.first_name, s.last_name"""
    ).fetchall()
    
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Admission", "First Name", "Last Name", "Class", "Section", "Bus", "Pickup Stop", "Drop Stop"])
    
    for row in rows:
        writer.writerow([
            row[1],   # admission_number
            row[2],   # first_name
            row[3],   # last_name
            row[4],   # class_name
            row[5],   # section
            row[9] or "N/A",  # bus_code
            row[10] or "N/A",  # pickup_stop
            row[11] or "N/A",  # drop_stop
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"}
    )
