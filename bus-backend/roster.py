"""
Roster sync endpoints - full roster distribution (§12).
Every Pi gets the complete roster on sync.
"""

import json
from fastapi import APIRouter

from database import get_conn

router = APIRouter(prefix="/api", tags=["roster"])


@router.get("/bus/{bus_id}/roster")
def get_roster(bus_id: str):
    """
    Full roster sync for a bus (§12: roster filtered by bus assignment).
    Returns only students assigned to this bus_id for pickup/drop tracking.
    """
    conn = get_conn()
    # Filter by assigned_bus_id to reduce unnecessary data transfer and memory usage
    rows = conn.execute(
        "SELECT * FROM students WHERE assigned_bus_id=? OR assigned_bus_id IS NULL",
        (bus_id,)
    ).fetchall()
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
