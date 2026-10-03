"""
New normalized data models for SFace.

Core principle: Use numeric/UUID primary keys internally.
Human-readable codes (BUS-014, STOP-023) are separate display identifiers.
Never compare arbitrary strings - always use proper relationships.

Phase 1 tables:
- schools
- buses
- routes
- stops
- students
- guardians
- transport_assignments
- face_profiles
- face_encodings
- attendance_events
- devices
- review_cases
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Text
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum

Base = declarative_base()


class School(Base):
    """School entity - root of all data"""
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    address = Column(String(500))
    timezone = Column(String(50), default="Asia/Kolkata")
    status = Column(String(20), default="active")  # active, inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bus(Base):
    """Bus entity - physical vehicle"""
    __tablename__ = "buses"
    
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    code = Column(String(50), nullable=False)  # BUS-014, display identifier
    name = Column(String(255))  # "Bus 14" or "Route A Bus"
    registration_number = Column(String(50), unique=True)  # Vehicle number
    device_id = Column(String(100), unique=True)  # Links to Raspberry Pi device (bus_14)
    capacity = Column(Integer, default=50)
    status = Column(String(20), default="active")  # active, inactive, maintenance
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Route(Base):
    """Route entity - logical bus route"""
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    code = Column(String(50), nullable=False)  # ROUTE-A, ROUTE-B
    name = Column(String(255), nullable=False)  # "Route A - North Wing"
    direction = Column(String(50))  # "morning", "afternoon"
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Stop(Base):
    """Stop entity - pickup/drop location"""
    __tablename__ = "stops"
    
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    code = Column(String(50), nullable=False)  # STOP-023
    name = Column(String(255), nullable=False)  # "KPHB Colony Gate"
    latitude = Column(Float)
    longitude = Column(Float)
    geofence_radius = Column(Integer, default=125)  # meters
    address = Column(String(500))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RouteStop(Base):
    """Stop sequence on a route"""
    __tablename__ = "route_stops"
    
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    sequence = Column(Integer)  # Order on route (1, 2, 3...)
    planned_time = Column(String(5))  # "07:30" pickup time


class Student(Base):
    """Student entity - core profile"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    admission_number = Column(String(50), nullable=False, unique=True)  # GNIT-2026-047
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    date_of_birth = Column(String(10))  # YYYY-MM-DD
    class_name = Column(String(10))  # "5", "6A", etc.
    section = Column(String(10))  # "A", "B", etc.
    profile_photo = Column(String(255))  # Path to photo
    gender = Column(String(10))  # "M", "F", "Other"
    status = Column(String(20), default="active")  # active, inactive, graduated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Guardian(Base):
    """Guardian entity - parent/emergency contact"""
    __tablename__ = "guardians"
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    name = Column(String(255), nullable=False)
    relationship = Column(String(50))  # "Father", "Mother", "Uncle", etc.
    phone = Column(String(20))
    email = Column(String(100))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransportAssignment(Base):
    """Transport assignment - where student travels"""
    __tablename__ = "transport_assignments"
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    pickup_stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    drop_stop_id = Column(Integer, ForeignKey("stops.id"), nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime)
    morning_enabled = Column(Boolean, default=True)
    afternoon_enabled = Column(Boolean, default=True)
    status = Column(String(20), default="active")  # active, suspended, ended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FaceProfile(Base):
    """Face biometric profile - separate from student"""
    __tablename__ = "face_profiles"
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, active, disabled, re-enroll
    encoding_version = Column(Integer, default=1)
    encoding_count = Column(Integer, default=0)
    quality_score = Column(Float)  # 0.0 - 1.0
    enrolled_at = Column(DateTime)
    enrolled_by = Column(String(100))  # admin ID
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FaceEncoding(Base):
    """Individual face encoding vector"""
    __tablename__ = "face_encodings"
    
    id = Column(Integer, primary_key=True)
    face_profile_id = Column(Integer, ForeignKey("face_profiles.id"), nullable=False)
    encoding = Column(Text)  # JSON array of 128-d vector
    quality_score = Column(Float)
    source_photo = Column(String(255))  # Path to source photo
    created_at = Column(DateTime, default=datetime.utcnow)


class Device(Base):
    """Device entity - Raspberry Pi on a bus"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    device_code = Column(String(100), unique=True)  # bus_14, pi_01
    ip_address = Column(String(20))
    last_seen = Column(DateTime)
    software_version = Column(String(50))
    status = Column(String(20), default="offline")  # online, offline
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceEvent(Base):
    """Attendance event - when student is picked up/dropped"""
    __tablename__ = "attendance_events"
    
    id = Column(Integer, primary_key=True)
    event_uuid = Column(String(36), unique=True, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # PICKED_UP, DROPPED, DETECTED_OTHER_BUS
    timestamp = Column(DateTime, nullable=False)
    confidence = Column(Float)
    direction = Column(String(20))  # ENTERING, EXITING
    latitude = Column(Float)
    longitude = Column(Float)
    photo_path = Column(String(255))
    source_device = Column(String(100))  # device_code
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewCase(Base):
    """Review case - unmatched/ambiguous detection"""
    __tablename__ = "review_cases"
    
    id = Column(Integer, primary_key=True)
    event_uuid = Column(String(36), unique=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)  # NULL if unknown
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    case_type = Column(String(50), nullable=False)  # UNMATCHED, AMBIGUOUS, DUPLICATE
    confidence = Column(Float)
    evidence_path = Column(String(255))  # Photo path
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, rejected
    assigned_to = Column(String(100))  # admin email
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolution = Column(String(500))  # Admin notes
