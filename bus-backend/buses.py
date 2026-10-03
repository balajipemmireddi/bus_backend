"""
Bus management endpoints.

CRUD operations for buses:
- Numeric ID (primary key)
- Code: human-readable identifier (BUS-014)
- Device code: links to Raspberry Pi (bus_14, pi_01)
- Status: active, inactive, maintenance
"""

import datetime
from fastapi import APIRouter, HTTPException

from database import get_conn
from schemas import BusCreate, BusUpdate, BusResponse

router = APIRouter(prefix="/api", tags=["buses"])


@router.get("/buses")
def list_buses(school_id: int | None = None, status: str = "active"):
    """
    List all buses.
    Returns numeric IDs and human-readable codes.
    """
    conn = get_conn()
    
    query = "SELECT id, code, name, registration_number, device_id, capacity, status FROM buses WHERE status=?"
    params = [status]
    
    if school_id:
        query += " AND school_id=?"
        params.append(school_id)
    
    query += " ORDER BY code"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    buses = []
    for r in rows:
        buses.append({
            "id": r[0],
            "code": r[1],
            "name": r[2],
            "registration_number": r[3],
            "device_id": r[4],
            "capacity": r[5],
            "status": r[6],
            # Legacy field for compatibility
            "bus_id": r[1]  # code as legacy bus_id
        })
    
    return {
        "total": len(buses),
        "buses": buses
    }


@router.post("/buses")
def create_bus(data: BusCreate):
    """Create a new bus."""
    conn = get_conn()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        
        # Check if code already exists
        existing = conn.execute(
            "SELECT id FROM buses WHERE code=? AND school_id=?",
            (data.code, data.school_id)
        ).fetchone()
        
        if existing:
            conn.close()
            raise HTTPException(409, f"Bus code '{data.code}' already exists")
        
        cursor = conn.execute(
            """INSERT INTO buses 
               (school_id, code, name, registration_number, device_id, capacity, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.school_id, data.code, data.name, data.registration_number, 
             data.device_id, data.capacity, "active", now, now)
        )
        bus_id = cursor.lastrowid
        conn.commit()
        
        return {
            "status": "ok",
            "bus_id": bus_id,
            "code": data.code,
            "name": data.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Create bus failed: {str(e)}")
    finally:
        conn.close()


@router.get("/buses/{bus_id}")
def get_bus(bus_id: int):
    """Get a single bus's details."""
    conn = get_conn()
    
    row = conn.execute(
        """SELECT id, code, name, registration_number, device_id, capacity, status, created_at, updated_at, school_id
           FROM buses WHERE id=?""",
        (bus_id,)
    ).fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(404, f"Bus {bus_id} not found")
    
    return {
        "id": row[0],
        "code": row[1],
        "name": row[2],
        "registration_number": row[3],
        "device_id": row[4],
        "capacity": row[5],
        "status": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        "school_id": row[9],
        # Legacy field
        "bus_id": row[1]
    }


@router.put("/buses/{bus_id}")
def update_bus(bus_id: int, data: BusUpdate):
    """Update a bus's details."""
    conn = get_conn()
    
    # Check bus exists
    bus = conn.execute("SELECT id FROM buses WHERE id=?", (bus_id,)).fetchone()
    if not bus:
        conn.close()
        raise HTTPException(404, f"Bus {bus_id} not found")
    
    try:
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.registration_number is not None:
            updates["registration_number"] = data.registration_number
        if data.capacity is not None:
            updates["capacity"] = data.capacity
        if data.status is not None:
            updates["status"] = data.status
        
        if updates:
            now = datetime.datetime.utcnow().isoformat()
            updates["updated_at"] = now
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [bus_id]
            conn.execute(f"UPDATE buses SET {set_clause} WHERE id=?", values)
            conn.commit()
        
        return {"status": "ok", "bus_id": bus_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Update failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/buses/{bus_id}")
def delete_bus(bus_id: int):
    """Soft delete a bus (mark as inactive)."""
    conn = get_conn()
    
    # Check bus exists
    bus = conn.execute("SELECT id FROM buses WHERE id=?", (bus_id,)).fetchone()
    if not bus:
        conn.close()
        raise HTTPException(404, f"Bus {bus_id} not found")
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE buses SET status='inactive', updated_at=? WHERE id=?",
            (now, bus_id)
        )
        conn.commit()
        
        return {"status": "ok", "message": f"Bus {bus_id} deleted"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")
    finally:
        conn.close()
