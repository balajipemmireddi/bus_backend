"""
Bus Pickup/Drop Central Backend (Refactored)

Architecture:
- main.py: FastAPI app initialization and imports (you are here)
- database.py: DB connection, init, helpers
- schemas.py: Pydantic models
- enrollment.py: Student enrollment endpoints (/api/enroll, /api/enroll/centralized)
- roster.py: Roster sync endpoints (/api/bus/{bus_id}/roster)
- events.py: Event ingest and review queue (/api/events, /api/review, /api/live)
- devices.py: Device tracking (/api/devices, /api/devices/{bus_id}/heartbeat)
- students.py: CRUD operations and management (/api/students/*)
- dashboards.py: HTML dashboards (/dashboard, /management)
- image_utils.py: Image quality and encoding helpers

Deployment:
    pip install -r requirements.txt
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Or set via environment:
    export FACE_PROCESSOR_URL=http://192.168.1.85:8095  # Update to your Pi IP
    export DATABASE_URL=sqlite:///data/backend.db
"""

from fastapi import FastAPI
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Initialize database
from database import init_db
init_db()

# Create FastAPI app
app = FastAPI(
    title="Bus Pickup/Drop Backend",
    description="Centralized face recognition for school bus pickup/drop management",
    version="1.0.0"
)

# Import and include routers (each module handles its own endpoints)
from enrollment import router as enrollment_router
from roster import router as roster_router
from events import router as events_router
from devices import router as devices_router
from students import router as students_router
from dashboards import router as dashboards_router

app.include_router(enrollment_router)
app.include_router(roster_router)
app.include_router(events_router)
app.include_router(devices_router)
app.include_router(students_router)
app.include_router(dashboards_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    from students import students_health
    return students_health()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
