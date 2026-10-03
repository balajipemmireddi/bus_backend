"""
Enrollment endpoints - Phase 1 normalized enrollment workflow.

Five-step enrollment process:
1. Student basic info (name, DOB, class, etc.)
2. Guardian information (parent/emergency contact)
3. Transport assignment (bus, route, stops)
4. Face capture (photos from browser or camera)
5. Review and confirm enrollment

All steps collected into a single transaction for atomicity.
"""

import json
import requests
import datetime
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse

from database import get_conn
from schemas import (
    EnrollmentStep1_StudentInfo,
    EnrollmentStep2_Guardians,
    EnrollmentStep3_Transport,
    EnrollmentStep4_FaceCapture,
    EnrollmentStep5_Review,
)

router = APIRouter(prefix="/api", tags=["enrollment"])


def get_face_processor_url():
    """Get face processor URL from config."""
    import os
    return os.environ.get("FACE_PROCESSOR_URL", "http://192.168.1.85:8095")


def get_default_school_id(conn):
    """Get or create default school for enrollment."""
    row = conn.execute("SELECT id FROM schools LIMIT 1").fetchone()
    if row:
        return row[0]
    
    # Create default school if none exists
    now = datetime.datetime.utcnow().isoformat()
    cursor = conn.execute(
        """INSERT INTO schools (name, code, timezone, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("Default School", "DEFAULT", "Asia/Kolkata", "active", now, now)
    )
    return cursor.lastrowid


@router.post("/enrollment/step1")
def enrollment_step1(data: EnrollmentStep1_StudentInfo):
    """
    Step 1: Student basic information.
    Validates uniqueness of admission_number and returns session for next step.
    """
    conn = get_conn()
    
    # Check if admission_number already exists
    existing = conn.execute(
        "SELECT id FROM students WHERE admission_number=?",
        (data.admission_number,)
    ).fetchone()
    
    if existing:
        conn.close()
        raise HTTPException(
            409,
            f"Admission number '{data.admission_number}' already exists. "
            f"Use a different number or update the existing student."
        )
    
    conn.close()
    
    # Return session data for frontend to carry through steps
    return {
        "status": "ok",
        "step": 1,
        "session_data": {
            "admission_number": data.admission_number,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "date_of_birth": data.date_of_birth,
            "class_name": data.class_name,
            "section": data.section,
            "gender": data.gender,
        }
    }


@router.post("/enrollment/step2")
def enrollment_step2(admission_number: str, data: EnrollmentStep2_Guardians):
    """
    Step 2: Guardian information.
    Validates and prepares guardian records.
    """
    if not data.guardians:
        raise HTTPException(400, "At least one guardian is required")
    
    # Validate guardians have required fields
    for g in data.guardians:
        if not g.name:
            raise HTTPException(400, "Guardian name is required")
    
    return {
        "status": "ok",
        "step": 2,
        "guardians_count": len(data.guardians),
        "message": f"Recorded {len(data.guardians)} guardian(s)"
    }


@router.post("/enrollment/step3")
def enrollment_step3(admission_number: str, data: EnrollmentStep3_Transport):
    """
    Step 3: Transport assignment (bus, route, stops).
    Validates bus, route, and stops exist.
    """
    conn = get_conn()
    
    # Validate bus exists
    bus = conn.execute("SELECT id FROM buses WHERE id=?", (data.bus_id,)).fetchone()
    if not bus:
        conn.close()
        raise HTTPException(404, f"Bus ID {data.bus_id} not found")
    
    # Validate route exists
    route = conn.execute("SELECT id FROM routes WHERE id=?", (data.route_id,)).fetchone()
    if not route:
        conn.close()
        raise HTTPException(404, f"Route ID {data.route_id} not found")
    
    # Validate pickup stop exists
    pickup = conn.execute("SELECT id FROM stops WHERE id=?", (data.pickup_stop_id,)).fetchone()
    if not pickup:
        conn.close()
        raise HTTPException(404, f"Pickup stop ID {data.pickup_stop_id} not found")
    
    # Validate drop stop exists
    drop = conn.execute("SELECT id FROM stops WHERE id=?", (data.drop_stop_id,)).fetchone()
    if not drop:
        conn.close()
        raise HTTPException(404, f"Drop stop ID {data.drop_stop_id} not found")
    
    conn.close()
    
    return {
        "status": "ok",
        "step": 3,
        "bus_id": data.bus_id,
        "route_id": data.route_id,
        "pickup_stop_id": data.pickup_stop_id,
        "drop_stop_id": data.drop_stop_id,
    }


@router.post("/enrollment/step4")
def enrollment_step4(admission_number: str, data: EnrollmentStep4_FaceCapture):
    """
    Step 4: Face capture - submit photos for encoding.
    Delegates to face_processor on Pi, gets encodings back.
    """
    if not data.photos:
        raise HTTPException(400, "At least one photo is required")
    
    # Delegate encoding to face_processor on Pi
    face_processor_url = get_face_processor_url()
    try:
        resp = requests.post(
            f"{face_processor_url}/encode",
            json={"photos": data.photos},
            timeout=120  # Pi can be slow
        )
        resp.raise_for_status()
        result = resp.json()
    except requests.exceptions.Timeout:
        raise HTTPException(
            504,
            f"Face processor timeout after 120s encoding {len(data.photos)} photo(s). "
            f"Try with fewer or better-lit photos."
        )
    except Exception as e:
        raise HTTPException(
            502,
            f"Could not reach face processor at {face_processor_url}: {e}"
        )
    
    encodings = result.get("encodings", [])
    rejections = result.get("rejections", [])
    
    if not encodings:
        raise HTTPException(
            400,
            f"No usable face encodings from {len(data.photos)} photo(s). "
            f"Rejections: {rejections}"
        )
    
    return {
        "status": "ok",
        "step": 4,
        "encodings_count": len(encodings),
        "photos_processed": len(data.photos),
        "rejections": rejections,
        "message": f"Successfully encoded {len(encodings)} face(s) from {len(data.photos)} photo(s)"
    }


@router.post("/enrollment/step5")
def enrollment_step5(
    admission_number: str,
    step1: EnrollmentStep1_StudentInfo,
    step2: EnrollmentStep2_Guardians,
    step3: EnrollmentStep3_Transport,
    encodings: list,  # From step 4 result
    step5: EnrollmentStep5_Review
):
    """
    Step 5: Complete enrollment - atomically create student, guardians, transport, face profile, and encodings.
    All-or-nothing transaction.
    """
    if not step5.confirmed:
        raise HTTPException(400, "Enrollment must be confirmed")
    
    conn = get_conn()
    try:
        # Get default school
        school_id = get_default_school_id(conn)
        now = datetime.datetime.utcnow().isoformat()
        
        # 1. Create student
        cursor = conn.execute(
            """INSERT INTO students 
               (school_id, admission_number, first_name, last_name, date_of_birth, 
                class_name, section, gender, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (school_id, step1.admission_number, step1.first_name, step1.last_name,
             step1.date_of_birth, step1.class_name, step1.section, step1.gender,
             "active", now, now)
        )
        student_id = cursor.lastrowid
        
        # 2. Create guardians
        guardian_ids = []
        for i, g in enumerate(step2.guardians):
            cursor = conn.execute(
                """INSERT INTO guardians 
                   (student_id, name, relationship, phone, email, is_primary, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, g.name, g.relationship, g.phone, g.email,
                 (i == 0), now, now)  # First guardian is primary
            )
            guardian_ids.append(cursor.lastrowid)
        
        # 3. Create transport assignment
        valid_from = datetime.datetime.utcnow().isoformat()
        cursor = conn.execute(
            """INSERT INTO transport_assignments
               (student_id, bus_id, route_id, pickup_stop_id, drop_stop_id,
                valid_from, morning_enabled, afternoon_enabled, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, step3.bus_id, step3.route_id, step3.pickup_stop_id, step3.drop_stop_id,
             valid_from, step3.morning_enabled, step3.afternoon_enabled,
             "active", now, now)
        )
        
        # 4. Create face profile
        cursor = conn.execute(
            """INSERT INTO face_profiles
               (student_id, status, encoding_count, quality_score, enrolled_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (student_id, "active", len(encodings), 1.0, now, now)
        )
        face_profile_id = cursor.lastrowid
        
        # 5. Store face encodings
        for encoding in encodings:
            enc_json = json.dumps(encoding)
            conn.execute(
                """INSERT INTO face_encodings
                   (face_profile_id, encoding, quality_score, created_at)
                   VALUES (?, ?, ?, ?)""",
                (face_profile_id, enc_json, 1.0, now)
            )
        
        conn.commit()
        
        return {
            "status": "success",
            "student_id": student_id,
            "admission_number": step1.admission_number,
            "first_name": step1.first_name,
            "last_name": step1.last_name,
            "guardians": len(guardian_ids),
            "encodings": len(encodings),
            "message": f"Enrolled {step1.first_name} {step1.last_name} with {len(encodings)} face encodings"
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Enrollment failed: {str(e)}")
    
    finally:
        conn.close()
