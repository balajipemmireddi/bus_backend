"""
Enrollment endpoints - handles both direct /api/enroll and centralized enrollment.
Delegates face encoding to face_processor.py on the Pi.
"""

import json
import requests
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse

from database import get_conn
from schemas import StudentIn, CentralEnrollmentIn

router = APIRouter(prefix="/api", tags=["enrollment"])


def get_face_processor_url():
    """Get face processor URL from config."""
    import os
    return os.environ.get("FACE_PROCESSOR_URL", "http://192.168.1.85:8095")


@router.post("/enroll")
def enroll(student: StudentIn):
    """
    Direct enrollment with pre-encoded face data.
    (Used by Pi enrollment dashboard after local encoding.)
    """
    conn = get_conn()
    existing = conn.execute("SELECT name FROM students WHERE child_id=?", (student.child_id,)).fetchone()
    if existing and existing["name"] != student.name:
        conn.close()
        raise HTTPException(
            409,
            f"child_id '{student.child_id}' already belongs to '{existing['name']}'. "
            f"Enrolling '{student.name}' under this ID would overwrite them. "
            f"Use a different child_id, or explicitly confirm the overwrite."
        )
    
    conn.execute(
        """INSERT INTO students (child_id, name, encodings, assigned_bus_id, pickup_stop_id, drop_stop_id, twin_group)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(child_id) DO UPDATE SET
             name=excluded.name, encodings=excluded.encodings,
             assigned_bus_id=excluded.assigned_bus_id,
             pickup_stop_id=excluded.pickup_stop_id, drop_stop_id=excluded.drop_stop_id,
             twin_group=excluded.twin_group""",
        (student.child_id, student.name, json.dumps(student.encodings),
         student.assigned_bus_id, student.pickup_stop_id, student.drop_stop_id, student.twin_group),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "child_id": student.child_id}


@router.post("/enroll/centralized")
def centralized_enroll(data: CentralEnrollmentIn):
    """
    Centralized enrollment: browser sends base64 photos to backend, which forwards
    them to face_processor.py on the Pi (NOT processed here - backend never imports
    face_recognition/dlib, avoiding Windows dlib install problems entirely).
    Pi does quality checks + encoding and returns the result; backend just stores it.
    """
    if not data.photos:
        raise HTTPException(400, "No photos provided")

    # Check for existing student collision
    conn = get_conn()
    existing = conn.execute("SELECT name FROM students WHERE child_id=?", (data.child_id,)).fetchone()
    conn.close()
    
    if existing and existing["name"] != data.name and not data.force_overwrite:
        return JSONResponse(
            status_code=409,
            content={
                "status": "error",
                "message": f"child_id '{data.child_id}' already belongs to '{existing['name']}'. "
                           f"Enrolling '{data.name}' under this ID would silently overwrite their "
                           f"face data. Pick a different child_id for this student, or confirm the "
                           f"overwrite if this really is meant to replace that record.",
                "collision": True,
                "existing_name": existing["name"],
            },
        )

    # Delegate encoding to face_processor on Pi
    face_processor_url = get_face_processor_url()
    try:
        resp = requests.post(
            f"{face_processor_url}/encode",
            json={"photos": data.photos},
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "message": f"Could not reach face processor at {face_processor_url} "
                           f"(is face_processor.py running on the Pi?): {e}"
            },
        )

    good_encodings = result.get("encodings", [])
    rejections = result.get("rejections", [])

    if not good_encodings:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"No usable photos. Rejections: {rejections}"
            },
        )

    # Store in database
    conn = get_conn()
    conn.execute(
        """INSERT INTO students (child_id, name, encodings, assigned_bus_id, pickup_stop_id, drop_stop_id, twin_group)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(child_id) DO UPDATE SET
             name=excluded.name, encodings=excluded.encodings,
             assigned_bus_id=excluded.assigned_bus_id,
             pickup_stop_id=excluded.pickup_stop_id, drop_stop_id=excluded.drop_stop_id,
             twin_group=excluded.twin_group""",
        (data.child_id, data.name, json.dumps(good_encodings),
         data.bus_id, data.pickup_stop_id, data.drop_stop_id, data.twin_group),
    )
    conn.commit()
    conn.close()

    summary = f"Enrolled '{data.name}' with {len(good_encodings)} encodings from {len(data.photos)} photos."
    if rejections:
        summary += f"\n\nRejected: {', '.join(rejections)}"

    return {
        "status": "success",
        "child_id": data.child_id,
        "encodings_count": len(good_encodings),
        "message": summary
    }
