"""
Device tracking endpoints - monitors which Pi devices are online/offline.

Each device is identified by device_code (e.g., "bus_14") and maps to a bus_id.
Heartbeat endpoint tracks online/offline status.
"""

import datetime
from fastapi import APIRouter, HTTPException

from database import get_conn

router = APIRouter(prefix="/api", tags=["devices"])


@router.post("/devices/{device_code}/heartbeat")
def device_heartbeat(device_code: str, ip_address: str | None = None, software_version: str | None = None):
    """
    Called by edge devices to report they're online.
    Device code format: "bus_14", "pi_01", etc.
    """
    conn = get_conn()
    now = datetime.datetime.utcnow().isoformat()
    
    try:
        # Get device by code
        device = conn.execute(
            "SELECT id, bus_id FROM devices WHERE device_code=?",
            (device_code,)
        ).fetchone()
        
        if device:
            # Update existing device
            updates = {"last_seen": now, "status": "online"}
            if ip_address:
                updates["ip_address"] = ip_address
            if software_version:
                updates["software_version"] = software_version
            
            set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
            values = list(updates.values()) + [device["id"]]
            conn.execute(f"UPDATE devices SET {set_clause} WHERE id=?", values)
        else:
            # Create new device entry
            # Extract bus number from device code (e.g., "bus_14" → 14)
            try:
                bus_num = int(device_code.split("_")[-1])
                # Try to find corresponding bus
                bus = conn.execute(
                    """SELECT id FROM buses WHERE id=? OR code LIKE ? OR code LIKE ?""",
                    (bus_num, f"BUS-%{bus_num}", f"BUS-{bus_num:03d}")
                ).fetchone()
                bus_id = bus["id"] if bus else None
            except:
                bus_id = None
            
            cursor = conn.execute(
                """INSERT INTO devices 
                   (bus_id, device_code, ip_address, last_seen, software_version, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (bus_id, device_code, ip_address, now, software_version, "online", now, now)
            )
        
        conn.commit()
        
        return {
            "status": "ok",
            "device_code": device_code,
            "message": "Heartbeat recorded"
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Heartbeat failed: {str(e)}")
    finally:
        conn.close()


@router.get("/devices")
def get_devices(status: str | None = None):
    """
    Get all devices with current status.
    Marks offline if no heartbeat in last 2 minutes.
    """
    conn = get_conn()
    
    query = """SELECT d.id, d.device_code, d.bus_id, d.ip_address, d.last_seen, 
                      d.software_version, d.status, b.code as bus_code
               FROM devices d
               LEFT JOIN buses b ON b.id = d.bus_id
               ORDER BY d.device_code"""
    
    rows = conn.execute(query).fetchall()
    conn.close()
    
    devices = []
    now = datetime.datetime.utcnow()
    
    for r in rows:
        # Determine actual status based on last heartbeat
        last_seen = r[4]
        if last_seen:
            try:
                last_seen_time = datetime.datetime.fromisoformat(last_seen)
                age_seconds = (now - last_seen_time).total_seconds()
                actual_status = "online" if age_seconds < 120 else "offline"
            except:
                actual_status = r[6]
        else:
            actual_status = "unknown"
        
        if status and actual_status != status:
            continue
        
        devices.append({
            "id": r[0],
            "device_code": r[1],
            "bus_id": r[2],
            "bus_code": r[7],
            "ip_address": r[3],
            "last_seen": r[4],
            "software_version": r[5],
            "status": actual_status
        })
    
    return {
        "total": len(devices),
        "devices": devices
    }


@router.get("/devices/{device_code}")
def get_device(device_code: str):
    """Get details for a specific device."""
    conn = get_conn()
    
    row = conn.execute(
        """SELECT d.id, d.device_code, d.bus_id, d.ip_address, d.last_seen, 
                  d.software_version, d.status, d.created_at, d.updated_at, b.code as bus_code
           FROM devices d
           LEFT JOIN buses b ON b.id = d.bus_id
           WHERE d.device_code=?""",
        (device_code,)
    ).fetchone()
    
    conn.close()
    
    if not row:
        raise HTTPException(404, f"Device {device_code} not found")
    
    # Check if online
    now = datetime.datetime.utcnow()
    if row[4]:
        try:
            last_seen_time = datetime.datetime.fromisoformat(row[4])
            age_seconds = (now - last_seen_time).total_seconds()
            actual_status = "online" if age_seconds < 120 else "offline"
        except:
            actual_status = row[6]
    else:
        actual_status = "unknown"
    
    return {
        "id": row[0],
        "device_code": row[1],
        "bus_id": row[2],
        "bus_code": row[9],
        "ip_address": row[3],
        "last_seen": row[4],
        "software_version": row[5],
        "status": actual_status,
        "created_at": row[7],
        "updated_at": row[8]
    }
