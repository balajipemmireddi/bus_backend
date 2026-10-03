"""
Route management endpoints.

CRUD operations for routes:
- Numeric ID (primary key)
- Code: human-readable identifier (ROUTE-A, ROUTE-B)
- Direction: morning, afternoon, or both
- Contains multiple stops in sequence
"""

import datetime
from fastapi import APIRouter, HTTPException

from database import get_conn
from schemas import RouteCreate, RouteUpdate, RouteResponse

router = APIRouter(prefix="/api", tags=["routes"])


@router.get("/routes")
def list_routes(school_id: int | None = None, status: str = "active"):
    """
    List all routes.
    """
    conn = get_conn()
    
    query = "SELECT id, code, name, direction, status FROM routes WHERE status=?"
    params = [status]
    
    if school_id:
        query += " AND school_id=?"
        params.append(school_id)
    
    query += " ORDER BY code"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    routes = []
    for r in rows:
        routes.append({
            "id": r[0],
            "code": r[1],
            "name": r[2],
            "direction": r[3],
            "status": r[4]
        })
    
    return {
        "total": len(routes),
        "routes": routes
    }


@router.post("/routes")
def create_route(data: RouteCreate):
    """Create a new route."""
    conn = get_conn()
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        
        # Check if code already exists
        existing = conn.execute(
            "SELECT id FROM routes WHERE code=? AND school_id=?",
            (data.code, data.school_id)
        ).fetchone()
        
        if existing:
            conn.close()
            raise HTTPException(409, f"Route code '{data.code}' already exists")
        
        cursor = conn.execute(
            """INSERT INTO routes 
               (school_id, code, name, direction, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data.school_id, data.code, data.name, data.direction, "active", now, now)
        )
        route_id = cursor.lastrowid
        conn.commit()
        
        return {
            "status": "ok",
            "route_id": route_id,
            "code": data.code,
            "name": data.name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Create route failed: {str(e)}")
    finally:
        conn.close()


@router.get("/routes/{route_id}")
def get_route(route_id: int):
    """Get a single route's details with stops."""
    conn = get_conn()
    
    row = conn.execute(
        """SELECT id, code, name, direction, status, created_at, updated_at, school_id
           FROM routes WHERE id=?""",
        (route_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(404, f"Route {route_id} not found")
    
    # Get stops on this route
    stops_rows = conn.execute(
        """SELECT s.id, s.code, s.name, rs.sequence, rs.planned_time
           FROM route_stops rs
           JOIN stops s ON s.id = rs.stop_id
           WHERE rs.route_id = ?
           ORDER BY rs.sequence""",
        (route_id,)
    ).fetchall()
    
    conn.close()
    
    stops = [
        {
            "stop_id": s[0],
            "code": s[1],
            "name": s[2],
            "sequence": s[3],
            "planned_time": s[4]
        }
        for s in stops_rows
    ]
    
    return {
        "id": row[0],
        "code": row[1],
        "name": row[2],
        "direction": row[3],
        "status": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "school_id": row[7],
        "stops": stops
    }


@router.put("/routes/{route_id}")
def update_route(route_id: int, data: RouteUpdate):
    """Update a route's details."""
    conn = get_conn()
    
    # Check route exists
    route = conn.execute("SELECT id FROM routes WHERE id=?", (route_id,)).fetchone()
    if not route:
        conn.close()
        raise HTTPException(404, f"Route {route_id} not found")
    
    try:
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.direction is not None:
            updates["direction"] = data.direction
        if data.status is not None:
            updates["status"] = data.status
        
        if updates:
            now = datetime.datetime.utcnow().isoformat()
            updates["updated_at"] = now
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [route_id]
            conn.execute(f"UPDATE routes SET {set_clause} WHERE id=?", values)
            conn.commit()
        
        return {"status": "ok", "route_id": route_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Update failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/routes/{route_id}")
def delete_route(route_id: int):
    """Soft delete a route (mark as inactive)."""
    conn = get_conn()
    
    # Check route exists
    route = conn.execute("SELECT id FROM routes WHERE id=?", (route_id,)).fetchone()
    if not route:
        conn.close()
        raise HTTPException(404, f"Route {route_id} not found")
    
    try:
        now = datetime.datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE routes SET status='inactive', updated_at=? WHERE id=?",
            (now, route_id)
        )
        conn.commit()
        
        return {"status": "ok", "message": f"Route {route_id} deleted"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")
    finally:
        conn.close()


@router.post("/routes/{route_id}/stops")
def add_stop_to_route(route_id: int, stop_id: int, sequence: int, planned_time: str | None = None):
    """Add a stop to a route."""
    conn = get_conn()
    
    try:
        # Validate route exists
        route = conn.execute("SELECT id FROM routes WHERE id=?", (route_id,)).fetchone()
        if not route:
            conn.close()
            raise HTTPException(404, f"Route {route_id} not found")
        
        # Validate stop exists
        stop = conn.execute("SELECT id FROM stops WHERE id=?", (stop_id,)).fetchone()
        if not stop:
            conn.close()
            raise HTTPException(404, f"Stop {stop_id} not found")
        
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM route_stops WHERE route_id=? AND stop_id=?",
            (route_id, stop_id)
        ).fetchone()
        
        if existing:
            conn.close()
            raise HTTPException(409, f"Stop {stop_id} already on route {route_id}")
        
        cursor = conn.execute(
            """INSERT INTO route_stops (route_id, stop_id, sequence, planned_time)
               VALUES (?, ?, ?, ?)""",
            (route_id, stop_id, sequence, planned_time)
        )
        conn.commit()
        
        return {
            "status": "ok",
            "route_id": route_id,
            "stop_id": stop_id,
            "sequence": sequence
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Add stop failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/routes/{route_id}/stops/{stop_id}")
def remove_stop_from_route(route_id: int, stop_id: int):
    """Remove a stop from a route."""
    conn = get_conn()
    
    try:
        conn.execute(
            "DELETE FROM route_stops WHERE route_id=? AND stop_id=?",
            (route_id, stop_id)
        )
        conn.commit()
        
        return {"status": "ok", "message": f"Stop removed from route"}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Remove stop failed: {str(e)}")
    finally:
        conn.close()
