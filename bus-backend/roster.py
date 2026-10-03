"""
Roster sync endpoints - full roster distribution to Pi devices.

Each Pi receives only students assigned to its bus.
Includes face encodings for recognition.

Format for Pi (backward compatible):
{
  "student_id": 47,  (numeric ID - Pi uses this internally)
  "admission_number": "GNIT-2026-047",
  "first_name": "Balu",
  "last_name": "Kumar",
  "bus_id": 14,
  "pickup_stop_id": 23,
  "drop_stop_id": 25,
  "encodings": [...]
}
"""

import json
import datetime
from fastapi import APIRouter, HTTPException

from database import get_conn

router = APIRouter(prefix="/api", tags=["roster"])


@router.get("/bus/{bus_id}/roster")
def get_roster(bus_id: int):
    """
    Full roster sync for a bus.
    Returns all active students assigned to this bus with their face encodings.
    
    bus_id: numeric bus ID (e.g., 14 for BUS-014)
    """
    conn = get_conn()
    
    try:
        # Validate bus exists
        bus = conn.execute("SELECT id, code FROM buses WHERE id=?", (bus_id,)).fetchone()
        if not bus:
            conn.close()
            raise HTTPException(404, f"Bus {bus_id} not found")
        
        # Get all students for this bus with their current transport and face encodings
        students_query = """
            SELECT 
                s.id as student_id,
                s.admission_number,
                s.first_name,
                s.last_name,
                ta.bus_id,
                ta.pickup_stop_id,
                ta.drop_stop_id,
                ta.morning_enabled,
                ta.afternoon_enabled,
                fp.id as face_profile_id,
                s.class_name,
                s.section
            FROM students s
            JOIN transport_assignments ta ON ta.student_id = s.id
            JOIN face_profiles fp ON fp.student_id = s.id
            WHERE ta.bus_id = ? AND ta.status = 'active' AND s.status = 'active'
            ORDER BY s.first_name, s.last_name
        """
        
        students = conn.execute(students_query, (bus_id,)).fetchall()
        roster = []
        
        for student in students:
            student_id = student[0]
            face_profile_id = student[9]
            
            # Get face encodings for this student
            encodings_query = """
                SELECT encoding FROM face_encodings 
                WHERE face_profile_id = ?
                ORDER BY id
            """
            encoding_rows = conn.execute(encodings_query, (face_profile_id,)).fetchall()
            
            encodings = []
            for enc_row in encoding_rows:
                try:
                    encoding_data = json.loads(enc_row[0])
                    encodings.append(encoding_data)
                except:
                    pass
            
            if not encodings:
                # Skip students without encodings
                continue
            
            # Build roster entry
            roster_entry = {
                "student_id": student_id,
                "admission_number": student[1],
                "first_name": student[2],
                "last_name": student[3],
                "bus_id": student[4],
                "pickup_stop_id": student[5],
                "drop_stop_id": student[6],
                "encodings": encodings,
                "morning_enabled": bool(student[7]),
                "afternoon_enabled": bool(student[8]),
                "class_name": student[10],
                "section": student[11],
            }
            roster.append(roster_entry)
        
        conn.close()
        
        return {
            "bus_id": bus_id,
            "bus_code": bus[1],
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "student_count": len(roster),
            "students": roster
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(500, f"Roster fetch failed: {str(e)}")


@router.get("/device/{device_code}/roster")
def get_roster_by_device(device_code: str):
    """
    Get roster for a device identified by device code (e.g., "bus_14").
    """
    conn = get_conn()
    
    try:
        # Look up device to get bus_id
        device = conn.execute(
            "SELECT bus_id FROM devices WHERE device_code=?",
            (device_code,)
        ).fetchone()
        
        if not device or not device[0]:
            conn.close()
            raise HTTPException(404, f"Device {device_code} not assigned to a bus")
        
        bus_id = device[0]
        conn.close()
        
        # Use the main roster endpoint
        return get_roster(bus_id)
    
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(500, f"Device roster fetch failed: {str(e)}")
