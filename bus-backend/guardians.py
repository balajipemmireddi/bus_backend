"""
Guardian management endpoints.

CRUD operations for guardians (parents, emergency contacts):
- Associated with student
- Primary/secondary designation
- Contact information (phone, email)
"""

import datetime
from fastapi import APIRouter, HTTPException

from database import get_conn
from schemas import GuardianCreate, GuardianUpdate, GuardianResponse

router = APIRouter(prefix="/api", tags=["guardians"])


@router.get("/guardians")
def list_guardians(student_id: int | None = None):
    """
    List all guardians, optionally filtered by student.
    """
    conn = get_conn()
    
    query = "SELECT id, student_id, name, relationship, phone, email, is_primary, created_at, updated_at FROM guardians"
    params = []
    
    if student_id:
        query += " WHERE student_id=?"
        params.append(student_id)
    
    query += " ORDER BY is_primary DESC, name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    guardians = []
    for r in rows:
        guardians.append({
            "id": r[0],
            "student_id": r[1],
            "name": r[2],
            "relationship": r[3],
            "phone": r[4],
            "email": r[5],
            "is_primary": bool(r[6]),
            "created_at": r[7],
            "updated_at": r[8]
        })
    
    return {
        "total": len(guardians),
        "guardians": guardians
    }


@router.post("/guardians")
def create_guardian(data: GuardianCreate):
    """Create a new guardian for a student."""
    conn = get_conn()
    
    try:
        # Validate student exists
        student = conn.execute("SELECT id FROM students WHERE id=?", (data.student_id,)).fetchone()
        if not student:
            conn.close()
            raise HTTPException(404, f"Student {data.student_id} not found")
        
        now = datetime.datetime.utcnow().isoformat()
        
        cursor = conn.execute(
            """INSERT INTO guardians 
               (student_id, name, relationship, phone, email, is_primary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.student_id, data.name, data.relationship, data.phone, data.email,
             data.is_primary, now, now)
        )
        guardian_id = cursor.lastrowid
        conn.commit()
        
        # If setting as primary, unset other primaries
        if data.is_primary:
            conn.execute(
                "UPDATE guardians SET is_primary=0 WHERE student_id=? AND id!=?",
                (data.student_id, guardian_id)
            )
            conn.commit()
        
        return {
            "status": "ok",
            "guardian_id": guardian_id,
            "student_id": data.student_id,
            "name": data.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Create guardian failed: {str(e)}")
    finally:
        conn.close()


@router.get("/guardians/{guardian_id}")
def get_guardian(guardian_id: int):
    """Get a single guardian's details."""
    conn = get_conn()
    
    row = conn.execute(
        """SELECT id, student_id, name, relationship, phone, email, is_primary, created_at, updated_at
           FROM guardians WHERE id=?""",
        (guardian_id,)
    ).fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(404, f"Guardian {guardian_id} not found")
    
    return {
        "id": row[0],
        "student_id": row[1],
        "name": row[2],
        "relationship": row[3],
        "phone": row[4],
        "email": row[5],
        "is_primary": bool(row[6]),
        "created_at": row[7],
        "updated_at": row[8]
    }


@router.put("/guardians/{guardian_id}")
def update_guardian(guardian_id: int, data: GuardianUpdate):
    """Update a guardian's information."""
    conn = get_conn()
    
    # Get current guardian
    guardian = conn.execute(
        "SELECT student_id FROM guardians WHERE id=?",
        (guardian_id,)
    ).fetchone()
    
    if not guardian:
        conn.close()
        raise HTTPException(404, f"Guardian {guardian_id} not found")
    
    student_id = guardian[0]
    
    try:
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.relationship is not None:
            updates["relationship"] = data.relationship
        if data.phone is not None:
            updates["phone"] = data.phone
        if data.email is not None:
            updates["email"] = data.email
        if data.is_primary is not None:
            updates["is_primary"] = int(data.is_primary)
        
        if updates:
            now = datetime.datetime.utcnow().isoformat()
            updates["updated_at"] = now
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [guardian_id]
            conn.execute(f"UPDATE guardians SET {set_clause} WHERE id=?", values)
            
            # If setting as primary, unset other primaries
            if data.is_primary:
                conn.execute(
                    "UPDATE guardians SET is_primary=0 WHERE student_id=? AND id!=?",
                    (student_id, guardian_id)
                )
            
            conn.commit()
        
        return {"status": "ok", "guardian_id": guardian_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Update failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/guardians/{guardian_id}")
def delete_guardian(guardian_id: int):
    """Delete a guardian."""
    conn = get_conn()
    
    # Check guardian exists
    guardian = conn.execute("SELECT id FROM guardians WHERE id=?", (guardian_id,)).fetchone()
    if not guardian:
        conn.close()
        raise HTTPException(404, f"Guardian {guardian_id} not found")
    
    try:
        conn.execute("DELETE FROM guardians WHERE id=?", (guardian_id,))
        conn.commit()
        
        return {"status": "ok", "message": f"Guardian {guardian_id} deleted"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")
    finally:
        conn.close()
