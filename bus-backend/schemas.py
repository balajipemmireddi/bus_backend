"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel


class StudentIn(BaseModel):
    """Schema for student enrollment via /api/enroll."""
    child_id: str
    name: str
    encodings: list[list[float]]
    assigned_bus_id: str
    pickup_stop_id: str
    drop_stop_id: str
    twin_group: str | None = None


class StudentUpdate(BaseModel):
    """Schema for updating a student."""
    name: str | None = None
    assigned_bus_id: str | None = None
    pickup_stop_id: str | None = None
    drop_stop_id: str | None = None
    twin_group: str | None = None


class EventIn(BaseModel):
    """Schema for event ingestion from edge devices."""
    child_id: str
    event_type: str  # PICKED_UP | DROPPED | EXIT_UNEXPECTED_LOCATION | UNMATCHED_REVIEW
    confidence: float
    photo_path: str | None = ""
    gps_lat: float | None = None
    gps_lng: float | None = None
    bus_id: str
    timestamp: str | None = None


class CentralEnrollmentIn(BaseModel):
    """Schema for centralized enrollment (backend processes photos)."""
    child_id: str
    name: str
    bus_id: str
    pickup_stop_id: str
    drop_stop_id: str
    twin_group: str | None = None
    photos: list[str]  # base64 encoded photos
    force_overwrite: bool = False


class DeviceHeartbeat(BaseModel):
    """Schema for device heartbeat."""
    bus_id: str
    status: str = "online"


class ReviewResolve(BaseModel):
    """Schema for resolving review queue items."""
    decision: str  # confirmed | rejected
    confirmed_child_id: str | None = None
