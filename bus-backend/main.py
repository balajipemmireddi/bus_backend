"""
Bus Pickup/Drop Central Backend (Phase 1 - Normalized Schema)

Architecture:
- main.py: FastAPI app initialization and imports (you are here)
- database.py: DB connection, init, schema migration
- schemas.py: Pydantic models (normalized)
- enrollment.py: 5-step enrollment workflow endpoints
- roster.py: Roster sync endpoints
- stops.py: Stop management CRUD
- buses.py: Bus management CRUD
- routes.py: Route management CRUD
- students.py: Student profile and directory endpoints
- guardians.py: Guardian management CRUD
- events.py: Event ingestion and review queue
- devices.py: Device tracking and heartbeats

Deployment:
    pip install -r requirements.txt
    python -m uvicorn main:app --host 0.0.0.0 --port 8000

Network:
    Set FACE_PROCESSOR_URL=http://192.168.1.85:8095 (Pi IP, not Windows)
    Set DATABASE_URL=sqlite:///data/backend.db
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
from stops import router as stops_router
from buses import router as buses_router
from routes import router as routes_router
from guardians import router as guardians_router

app.include_router(enrollment_router)
app.include_router(roster_router)
app.include_router(events_router)
app.include_router(devices_router)
app.include_router(students_router)
app.include_router(stops_router)
app.include_router(buses_router)
app.include_router(routes_router)
app.include_router(guardians_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        from database import get_conn
        conn = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        conn.close()
        return {
            "status": "ok",
            "service": "bus-backend",
            "student_count": count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
