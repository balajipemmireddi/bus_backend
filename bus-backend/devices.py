"""
Device tracking endpoints - monitors which Pi devices are online/offline.
"""

import datetime
from fastapi import APIRouter

from database import get_conn

router = APIRouter(prefix="/api", tags=["devices"])


@router.post("/devices/{bus_id}/heartbeat")
def device_heartbeat(bus_id: str):
    """Called by edge devices to report they're online."""
    conn = get_conn()
    now = datetime.datetime.now().isoformat()
    conn.execute(
        """INSERT INTO devices (bus_id, last_heartbeat, status)
           VALUES (?, ?, 'online')
           ON CONFLICT(bus_id) DO UPDATE SET
             last_heartbeat=excluded.last_heartbeat, status='online'""",
        (bus_id, now),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@router.get("/devices")
def get_devices():
    """Get all connected devices with current status."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM devices ORDER BY bus_id").fetchall()
    conn.close()
    
    devices = []
    for r in rows:
        last_beat = r["last_heartbeat"]
        # Mark offline if no heartbeat in last 2 minutes
        if last_beat:
            last_beat_time = datetime.datetime.fromisoformat(last_beat)
            if (datetime.datetime.now() - last_beat_time).total_seconds() > 120:
                status = "offline"
            else:
                status = r["status"]
        else:
            status = "unknown"
        
        devices.append({
            "bus_id": r["bus_id"],
            "status": status,
            "last_heartbeat": last_beat
        })
    
    return devices
