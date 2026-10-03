"""
Pydantic schemas for request/response validation.

Phase 1 Schemas: New normalized models for buses, routes, stops, students, guardians,
transport assignments, face profiles, and enrollment.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# School Schemas
class SchoolCreate(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    timezone: str = "Asia/Kolkata"


class SchoolResponse(BaseModel):
    id: int
    name: str
    code: str
    address: Optional[str] = None
    timezone: str
    status: str
    created_at: str
    updated_at: str


# Bus Schemas
class BusCreate(BaseModel):
    school_id: int
    code: str
    name: Optional[str] = None
    registration_number: Optional[str] = None
    device_id: Optional[str] = None
    capacity: int = 50


class BusUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None


class BusResponse(BaseModel):
    id: int
    school_id: int
    code: str
    name: Optional[str]
    registration_number: Optional[str]
    device_id: Optional[str]
    capacity: int
    status: str
    created_at: str
    updated_at: str


# Route Schemas
class RouteCreate(BaseModel):
    school_id: int
    code: str
    name: str
    direction: Optional[str] = None


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None


class RouteResponse(BaseModel):
    id: int
    school_id: int
    code: str
    name: str
    direction: Optional[str]
    status: str
    created_at: str
    updated_at: str


# Stop Schemas
class StopCreate(BaseModel):
    school_id: int
    code: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: int = 125
    address: Optional[str] = None


class StopUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: Optional[int] = None
    address: Optional[str] = None
    status: Optional[str] = None


class StopResponse(BaseModel):
    id: int
    school_id: int
    code: str
    name: str
    latitude: Optional[float]
    longitude: Optional[float]
    geofence_radius: int
    address: Optional[str]
    status: str
    created_at: str
    updated_at: str


# Student Schemas
class StudentCreate(BaseModel):
    school_id: int
    admission_number: str
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    class_name: Optional[str] = None
    section: Optional[str] = None
    gender: Optional[str] = None


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    class_name: Optional[str] = None
    section: Optional[str] = None
    profile_photo: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None


class StudentResponse(BaseModel):
    id: int
    school_id: int
    admission_number: str
    first_name: str
    last_name: Optional[str]
    date_of_birth: Optional[str]
    class_name: Optional[str]
    section: Optional[str]
    profile_photo: Optional[str]
    gender: Optional[str]
    status: str
    created_at: str
    updated_at: str


class StudentDetailResponse(StudentResponse):
    guardians: Optional[list] = []
    transport_assignments: Optional[list] = []
    face_profile: Optional[dict] = None


# Guardian Schemas
class GuardianCreate(BaseModel):
    student_id: int
    name: str
    relationship: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: bool = False


class GuardianUpdate(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: Optional[bool] = None


class GuardianResponse(BaseModel):
    id: int
    student_id: int
    name: str
    relationship: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_primary: bool
    created_at: str
    updated_at: str


# Transport Assignment Schemas
class TransportAssignmentCreate(BaseModel):
    student_id: int
    bus_id: int
    route_id: int
    pickup_stop_id: int
    drop_stop_id: int
    valid_from: str
    valid_until: Optional[str] = None
    morning_enabled: bool = True
    afternoon_enabled: bool = True


class TransportAssignmentUpdate(BaseModel):
    bus_id: Optional[int] = None
    route_id: Optional[int] = None
    pickup_stop_id: Optional[int] = None
    drop_stop_id: Optional[int] = None
    valid_until: Optional[str] = None
    morning_enabled: Optional[bool] = None
    afternoon_enabled: Optional[bool] = None
    status: Optional[str] = None


class TransportAssignmentResponse(BaseModel):
    id: int
    student_id: int
    bus_id: int
    route_id: int
    pickup_stop_id: int
    drop_stop_id: int
    valid_from: str
    valid_until: Optional[str]
    morning_enabled: bool
    afternoon_enabled: bool
    status: str
    created_at: str
    updated_at: str


# Face Profile Schemas
class FaceProfileResponse(BaseModel):
    id: int
    student_id: int
    status: str
    encoding_version: int
    encoding_count: int
    quality_score: Optional[float]
    enrolled_at: Optional[str]
    enrolled_by: Optional[str]
    updated_at: str


# Face Encoding Schemas
class FaceEncodingCreate(BaseModel):
    face_profile_id: int
    encoding: list[float]  # 128-d vector
    quality_score: Optional[float] = None
    source_photo: Optional[str] = None


class FaceEncodingResponse(BaseModel):
    id: int
    face_profile_id: int
    encoding: Optional[str]
    quality_score: Optional[float]
    source_photo: Optional[str]
    created_at: str


# Attendance Event Schemas
class AttendanceEventIn(BaseModel):
    event_uuid: Optional[str] = None
    student_id: int
    bus_id: int
    event_type: str
    timestamp: str
    confidence: Optional[float] = None
    direction: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_path: Optional[str] = None
    source_device: Optional[str] = None


class AttendanceEventResponse(BaseModel):
    id: int
    event_uuid: str
    student_id: int
    bus_id: int
    event_type: str
    timestamp: str
    confidence: Optional[float]
    direction: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    photo_path: Optional[str]
    source_device: Optional[str]
    created_at: str


# Review Case Schemas
class ReviewCaseResponse(BaseModel):
    id: int
    event_uuid: Optional[str]
    student_id: Optional[int]
    bus_id: int
    case_type: str
    confidence: Optional[float]
    evidence_path: Optional[str]
    status: str
    assigned_to: Optional[str]
    created_at: str
    resolved_at: Optional[str]
    resolution: Optional[str]


class ReviewCaseResolve(BaseModel):
    decision: str  # confirmed, rejected
    confirmed_student_id: Optional[int] = None
    resolution_notes: Optional[str] = None





# Enrollment Wizard Schemas (Phase 1 - Step-by-step enrollment)
class EnrollmentStep1_StudentInfo(BaseModel):
    """Step 1: Student basic information"""
    admission_number: str
    first_name: str
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    class_name: Optional[str] = None
    section: Optional[str] = None
    gender: Optional[str] = None


class EnrollmentStep2_Guardians(BaseModel):
    """Step 2: Guardian information"""
    guardians: list[GuardianCreate]


class EnrollmentStep3_Transport(BaseModel):
    """Step 3: Transport assignment"""
    bus_id: int
    route_id: int
    pickup_stop_id: int
    drop_stop_id: int
    morning_enabled: bool = True
    afternoon_enabled: bool = True


class EnrollmentStep4_FaceCapture(BaseModel):
    """Step 4: Face capture photos (base64 encoded)"""
    photos: list[str]  # Base64 encoded photos


class EnrollmentStep5_Review(BaseModel):
    """Step 5: Review and confirm enrollment"""
    confirmed: bool


# Directory/Search Schemas
class StudentDirectoryQuery(BaseModel):
    """Query parameters for student directory search."""
    search: Optional[str] = None
    class_filter: Optional[str] = None
    bus_filter: Optional[int] = None
    route_filter: Optional[int] = None
    status_filter: Optional[str] = "active"
    page: int = 1
    page_size: int = 20


class StudentDirectoryResponse(BaseModel):
    """Paginated student directory response."""
    total: int
    page: int
    page_size: int
    students: list[StudentResponse]
