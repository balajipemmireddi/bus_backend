"""
Stops management endpoints - geographic locations for pickup/drop.

Each stop has:
- Numeric ID (internal)
- Code (display, e.g., "STOP-023")
- Name, coordinates, geofence radius
- Status (active/inactive)

Synced to Pi for location-aware state machine decisions.
"""

from fastapi import APIRouter, HTTPException
from database import get_conn
from schemas import StopCreate, StopUpdate, StopResponse

router = APIRouter(prefix="/api", tags=["stops"])


@router.get("/stops")
def list_stops(school_id: int | None = None, status: str = "active"):
    """
    Get all stops with their coordinates.
    Returns new format with numeric IDs and codes.
    """
    conn = get_conn()
    
    query = "SELECT id, code, name, latitude, longitude, geofence_radius, status FROM stops WHERE status=?"
    params = [status]
    
    if school_id:
        query += " AND school_id=?"
        params.append(school_id)
    
    query += " ORDER BY code"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    stops = []
    for r in rows:
        stops.append({
            "id": r[0],
            "code": r[1],
            "name": r[2],
            "latitude": r[3],
            "longitude": r[4],
            "geofence_radius": r[5],
            "status": r[6],
            # Legacy field for Pi compatibility
            "stop_id": str(r[0]),
            "radius_m": r[5]
        })
    
    return {
        "total": len(stops),
        "stops": stops
    }


@router.post("/stops")
def create_stop(data: StopCreate):
    """Create a new stop."""
    conn = get_conn()
    
    try:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        
        cursor = conn.execute(
            """INSERT INTO stops 
               (school_id, code, name, latitude, longitude, geofence_radius, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.school_id, data.code, data.name, data.latitude, data.longitude,
             data.geofence_radius, "active", now, now)
        )
        stop_id = cursor.lastrowid
        conn.commit()
        
        return {
            "status": "ok",
            "stop_id": stop_id,
            "code": data.code,
            "name": data.name
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Create stop failed: {str(e)}")
    finally:
        conn.close()


@router.get("/stops/{stop_id}")
def get_stop(stop_id: int):
    """Get a single stop's details by ID."""
    conn = get_conn()
    
    row = conn.execute(
        """SELECT id, code, name, latitude, longitude, geofence_radius, status, created_at, updated_at
           FROM stops WHERE id=?""",
        (stop_id,)
    ).fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(404, f"Stop {stop_id} not found")
    
    return {
        "id": row[0],
        "code": row[1],
        "name": row[2],
        "latitude": row[3],
        "longitude": row[4],
        "geofence_radius": row[5],
        "status": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        # Legacy fields for Pi compatibility
        "stop_id": str(row[0]),
        "radius_m": row[5]
    }


@router.put("/stops/{stop_id}")
def update_stop(stop_id: int, data: StopUpdate):
    """Update a stop's details."""
    conn = get_conn()
    
    # Check stop exists
    stop = conn.execute("SELECT id FROM stops WHERE id=?", (stop_id,)).fetchone()
    if not stop:
        conn.close()
        raise HTTPException(404, f"Stop {stop_id} not found")
    
    try:
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.latitude is not None:
            updates["latitude"] = data.latitude
        if data.longitude is not None:
            updates["longitude"] = data.longitude
        if data.geofence_radius is not None:
            updates["geofence_radius"] = data.geofence_radius
        if data.address is not None:
            updates["address"] = data.address
        if data.status is not None:
            updates["status"] = data.status
        
        if updates:
            import datetime
            updates["updated_at"] = datetime.datetime.utcnow().isoformat()
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [stop_id]
            conn.execute(f"UPDATE stops SET {set_clause} WHERE id=?", values)
            conn.commit()
        
        return {"status": "ok", "stop_id": stop_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Update failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/stops/{stop_id}")
def delete_stop(stop_id: int):
    """Delete a stop (soft delete via status)."""
    conn = get_conn()
    
    # Check stop exists
    stop = conn.execute("SELECT id FROM stops WHERE id=?", (stop_id,)).fetchone()
    if not stop:
        conn.close()
        raise HTTPException(404, f"Stop {stop_id} not found")
    
    try:
        import datetime
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE stops SET status='inactive', updated_at=? WHERE id=?",
            (now, stop_id)
        )
        conn.commit()
        
        return {"status": "ok", "message": f"Stop {stop_id} deleted"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")
    finally:
        conn.close()
