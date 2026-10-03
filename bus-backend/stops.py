"""
Stops management endpoints - geographic locations for pickup/drop (§4).
Each stop has coordinates and a geofence radius for proximity verification.
"""

from fastapi import APIRouter
from database import get_conn

router = APIRouter(prefix="/api", tags=["stops"])


@router.get("/stops")
def list_stops():
    """
    Get all stops with their coordinates for geofence verification.
    Synced to Pi for location-aware state machine decisions.
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM stops").fetchall()
    conn.close()
    
    return [
        {
            "stop_id": r["stop_id"],
            "name": r["name"],
            "latitude": r["latitude"],
            "longitude": r["longitude"],
            "radius_m": r["radius_m"] or 125,
        }
        for r in rows
    ]


@router.get("/stops/{stop_id}")
def get_stop(stop_id: str):
    """Get a single stop's details."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM stops WHERE stop_id=?", (stop_id,)).fetchone()
    conn.close()
    
    if not row:
        return {"error": "Stop not found"}
    
    return {
        "stop_id": row["stop_id"],
        "name": row["name"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "radius_m": row["radius_m"] or 125,
    }
