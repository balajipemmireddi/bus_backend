"""
Minimal cloud backend - built for speed to get an end-to-end demo working fast.

Uses SQLite (not Postgres) deliberately, to skip DB server setup while racing a
deadline. Per the main spec (§4), swap to Postgres before real multi-bus production
use - SQLite's single-writer lock will bottleneck once several buses sync
concurrently. Swapping later just means changing the SQLAlchemy connection string;
the schema/queries below are written in plain-enough SQL to port easily.

Run:
    pip install fastapi uvicorn --break-system-packages
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /api/enroll                    - add/update a student + encodings
    GET  /api/bus/{bus_id}/roster        - full roster sync (every device gets everything, §12)
    POST /api/events                     - edge devices push queued events here
    GET  /api/review                     - list pending review-queue items
    POST /api/review/{event_id}/resolve  - staff confirms/rejects a review item
    GET  /api/live                       - latest event per bus, for the live feed (§10)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
import json
import datetime
from pathlib import Path
import requests
import base64
import io
import numpy as np
import cv2

DB_PATH = Path(__file__).parent / "data" / "backend.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# The backend NEVER imports face_recognition/dlib itself - all face encoding work
# is delegated to face_processor.py running on the Pi (where dlib is already
# proven working via piwheels). 
# 
# Set via environment variable: export FACE_PROCESSOR_URL=http://192.168.X.X:8095
# Or edit the default below to match your Pi's actual IP
import os
FACE_PROCESSOR_URL = os.environ.get("FACE_PROCESSOR_URL", "http://192.168.1.X:8095")  # ← UPDATE: your Pi IP

print(f"[INFO] Face processor URL: {FACE_PROCESSOR_URL}")

app = FastAPI(title="Bus Pickup/Drop Backend (dev)")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            child_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            encodings TEXT NOT NULL,
            assigned_bus_id TEXT,
            pickup_stop_id TEXT,
            drop_stop_id TEXT,
            twin_group TEXT
        );

        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL,
            radius_m REAL DEFAULT 125
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id TEXT,
            event_type TEXT NOT NULL,
            confidence REAL,
            photo_path TEXT,
            gps_lat REAL,
            gps_lng REAL,
            bus_id TEXT,
            timestamp TEXT NOT NULL,
            review_status TEXT DEFAULT 'n/a'  -- n/a | pending | confirmed | rejected
        );

        CREATE TABLE IF NOT EXISTS devices (
            bus_id TEXT PRIMARY KEY,
            last_heartbeat TEXT,
            status TEXT DEFAULT 'offline'  -- online | offline
        );

        CREATE TABLE IF NOT EXISTS enrollment_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id TEXT,
            name TEXT,
            bus_id TEXT,
            pickup_stop_id TEXT,
            drop_stop_id TEXT,
            twin_group TEXT,
            photos TEXT,  -- JSON list of base64 encoded photos
            status TEXT DEFAULT 'processing',  -- processing | completed | failed
            encodings TEXT,  -- JSON list of successful encodings
            error_msg TEXT,
            created_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


init_db()


# ---- Schemas ----

class StudentIn(BaseModel):
    child_id: str
    name: str
    encodings: list[list[float]]
    assigned_bus_id: str
    pickup_stop_id: str
    drop_stop_id: str
    twin_group: str | None = None


class EventIn(BaseModel):
    child_id: str
    event_type: str          # PICKED_UP | DROPPED | EXIT_UNEXPECTED_LOCATION | UNMATCHED_REVIEW
    confidence: float
    photo_path: str | None = ""
    gps_lat: float | None = None
    gps_lng: float | None = None
    bus_id: str
    timestamp: str | None = None


class CentralEnrollmentIn(BaseModel):
    child_id: str
    name: str
    bus_id: str
    pickup_stop_id: str
    drop_stop_id: str
    twin_group: str | None = None
    photos: list[str]  # base64 encoded photos


# Helper: Decode base64 image to OpenCV format
def base64_to_cv2(b64_str: str):
    try:
        img_data = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        return None


# Helper: Quality check on image
def quality_check_image(image):
    if image is None:
        return False, "Could not decode image"
    
    h, w = image.shape[:2]
    if h < 100 or w < 100:
        return False, f"Image too small: {w}x{h}"
    
    # Check for exactly one face using dlib via a simple check
    try:
        import face_recognition
        face_locations = face_recognition.face_locations(image, model="hog")
        if len(face_locations) != 1:
            return False, f"Expected 1 face, found {len(face_locations)}"
        
        # Sharpness check (Laplacian variance)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        if sharpness < 15.0:
            return False, f"Image too blurry (sharpness={sharpness:.1f}, need >15)"
        
        return True, "OK"
    except Exception as e:
        return False, str(e)


# Helper: Generate encoding from image
def get_encoding_from_image(image):
    try:
        import face_recognition
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return None, "No face detected or encoding failed"
        return encodings[0].tolist(), None
    except Exception as e:
        return None, str(e)


# ---- Enrollment ----

@app.post("/api/enroll")
def enroll(student: StudentIn):
    conn = get_conn()
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


# ---- Roster sync (§12: full roster to every device) ----

@app.get("/api/bus/{bus_id}/roster")
def get_roster(bus_id: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return [
        {
            "child_id": r["child_id"],
            "name": r["name"],
            "encodings": json.loads(r["encodings"]),
            "assigned_bus_id": r["assigned_bus_id"],
            "pickup_stop_id": r["pickup_stop_id"],
            "drop_stop_id": r["drop_stop_id"],
            "twin_group": r["twin_group"],
        }
        for r in rows
    ]


# ---- Event ingest (from edge devices via sync_client.py) ----

@app.post("/api/events")
def ingest_event(event: EventIn):
    conn = get_conn()
    review_status = "pending" if event.event_type == "UNMATCHED_REVIEW" else "n/a"
    ts = event.timestamp or datetime.datetime.now().isoformat()
    cur = conn.execute(
        """INSERT INTO events (child_id, event_type, confidence, photo_path, gps_lat, gps_lng, bus_id, timestamp, review_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event.child_id, event.event_type, event.confidence, event.photo_path,
         event.gps_lat, event.gps_lng, event.bus_id, ts, review_status),
    )
    conn.commit()
    event_id = cur.lastrowid
    conn.close()

    # In production: trigger the WhatsApp send here for PICKED_UP/DROPPED (§9, Phase 6 - not built yet)
    if event.event_type in ("PICKED_UP", "DROPPED"):
        print(f"[WOULD SEND WHATSAPP] {event.event_type} for {event.child_id} on {event.bus_id}")

    return {"status": "ok", "event_id": event_id}


# ---- Review queue (§9) ----

@app.get("/api/review")
def list_review_queue():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM events WHERE review_status='pending'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/review/{event_id}/resolve")
def resolve_review(event_id: int, decision: str, confirmed_child_id: str | None = None):
    if decision not in ("confirmed", "rejected"):
        raise HTTPException(400, "decision must be 'confirmed' or 'rejected'")
    conn = get_conn()
    if decision == "confirmed" and confirmed_child_id:
        conn.execute(
            "UPDATE events SET review_status=?, child_id=? WHERE id=?",
            (decision, confirmed_child_id, event_id),
        )
    else:
        conn.execute("UPDATE events SET review_status=? WHERE id=?", (decision, event_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ---- Live feed (§10 - always-on event feed) ----

@app.get("/api/live")
def live_feed(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Device Tracking (for dashboard) ----

@app.post("/api/devices/{bus_id}/heartbeat")
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


@app.get("/api/devices")
def get_devices():
    """Get all connected devices."""
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


@app.get("/")
def root():
    return {"status": "Bus backend running", "docs": "/docs"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Live enrollment dashboard with device tracking and event feed."""
    return """<!DOCTYPE html>
<html>
<head>
  <title>School Bus - Central Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: #0f2540; --navy-light: #16345c; --accent: #2f6fed; --accent-light: #eaf1ff;
      --green: #1fa971; --green-bg: #e8f9f1; --red: #e5484d; --red-bg: #fdecec;
      --blue-bg: #eaf1ff; --blue-text: #2f6fed;
      --ink: #0f172a; --muted: #64748b; --border: #e6eaf0; --bg: #f4f6fb; --card: #ffffff;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--ink); }

    .shell { display: flex; min-height: 100vh; }

    .sidebar { width: 240px; background: var(--navy); color: #fff; flex-shrink: 0; padding: 24px 0;
      display: flex; flex-direction: column; }
    .brand { display: flex; align-items: center; gap: 10px; padding: 0 24px 24px; font-weight: 800; font-size: 1.05rem;
      border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px; }
    .brand-badge { width: 34px; height: 34px; background: var(--accent); border-radius: 9px; display: flex;
      align-items: center; justify-content: center; font-size: 1.1rem; }

    .tab-btn { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; padding: 12px 24px;
      background: none; border: none; color: rgba(255,255,255,0.65); font-size: 0.92rem; font-weight: 500;
      cursor: pointer; border-left: 3px solid transparent; transition: all .15s; margin: 0; border-radius: 0; }
    .tab-btn:hover { background: rgba(255,255,255,0.05); color: #fff; }
    .tab-btn.active { background: rgba(47,111,237,0.15); color: #fff; border-left-color: var(--accent); }
    .tab-icon { width: 18px; text-align: center; }

    .main { flex: 1; padding: 32px 40px; max-width: 1100px; }
    .page-title { font-size: 1.5rem; font-weight: 800; margin-bottom: 4px; }
    .page-sub { color: var(--muted); font-size: 0.92rem; margin-bottom: 28px; }

    .tab-content { display: none; } .tab-content.active { display: block; }

    .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px;
      box-shadow: 0 1px 2px rgba(15,23,42,0.03); margin-bottom: 20px; }
    .card h3 { font-size: 1rem; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }

    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 22px; }
    .form-group label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.82rem; color: var(--ink); }
    input[type=text], select { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px;
      font-size: 0.92rem; font-family: inherit; background: #fbfcfe; transition: border-color .15s; }
    input[type=text]:focus, select:focus { outline: none; border-color: var(--accent); background: #fff; }

    video { width: 100%; max-width: 420px; border-radius: 10px; margin-bottom: 14px; display: block; background: #000; }
    canvas { display: none; }

    .photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 10px; margin: 14px 0; max-width: 420px; }
    .photo-thumb { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
    .photo-thumb img { width: 100%; height: 100%; object-fit: cover; }
    .photo-thumb .remove { position: absolute; top: 3px; right: 3px; background: rgba(0,0,0,0.6); color: white;
      border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 13px; line-height: 1; }

    button { padding: 10px 20px; background: var(--navy); color: white; border: none; border-radius: 8px;
      font-size: 0.88rem; font-weight: 600; cursor: pointer; margin-right: 8px; margin-bottom: 8px;
      font-family: inherit; transition: background .15s, transform .1s; }
    button:hover { background: var(--navy-light); }
    button:active { transform: scale(0.98); }
    button:disabled { background: #cbd3e0; cursor: not-allowed; }
    button[type=submit] { background: var(--accent); }
    button[type=submit]:hover { background: #2560d6; }
    .btn-secondary { background: #fff; color: var(--ink); border: 1px solid var(--border) !important; }
    .btn-secondary:hover { background: #f4f6fb; }

    .status { padding: 12px 16px; border-radius: 8px; margin: 14px 0; font-size: 0.88rem; font-weight: 500; }
    .status.success { background: var(--green-bg); color: #0d7a4f; }
    .status.error { background: var(--red-bg); color: #b3272b; }
    .status.info { background: var(--blue-bg); color: var(--blue-text); }

    .device-item { padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; display: flex;
      justify-content: space-between; align-items: center; margin-bottom: 10px; background: #fbfcfe; }
    .device-item:last-child { margin-bottom: 0; }
    .device-status { padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: .02em; }
    .device-status.online { background: var(--green-bg); color: #0d7a4f; }
    .device-status.offline { background: var(--red-bg); color: #b3272b; }
    .device-status.unknown { background: #f1f3f7; color: var(--muted); }
    .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }
    .dot.online { background: #1fa971; } .dot.offline { background: #e5484d; } .dot.unknown { background: #94a3b8; }

    .event-item { padding: 14px 16px; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 10px; background: #fbfcfe; }
    .event-item:last-child { margin-bottom: 0; }
    .event-header { display: flex; justify-content: space-between; margin-bottom: 6px; align-items: center; }
    .event-type { font-weight: 700; padding: 3px 10px; border-radius: 6px; font-size: 0.72rem; letter-spacing: .02em; }
    .event-type.PICKED_UP { background: var(--green-bg); color: #0d7a4f; }
    .event-type.DROPPED { background: var(--blue-bg); color: var(--blue-text); }
    .event-meta { font-size: 0.83rem; color: var(--muted); }
    .event-time { color: var(--muted); font-size: 0.78rem; margin-top: 4px; }

    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }
    th { background: #fbfcfe; font-weight: 700; color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: .04em; }
    tr:hover td { background: #fafbfd; }
    code { background: #f1f3f7; padding: 3px 7px; border-radius: 5px; font-size: 0.82rem; }
    .pill { background: var(--blue-bg); color: var(--blue-text); padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

    .search-input { max-width: 320px; margin-bottom: 16px; }
    .empty-state { padding: 32px; text-align: center; color: var(--muted); font-size: 0.9rem; }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><span class="brand-badge">🚌</span> Bus Central</div>
      <button class="tab-btn active" onclick="window.showTab('enroll')"><span class="tab-icon">➕</span> Enroll Student</button>
      <button class="tab-btn" onclick="window.showTab('students')"><span class="tab-icon">🎓</span> All Students</button>
      <button class="tab-btn" onclick="window.showTab('devices')"><span class="tab-icon">📡</span> Connected Devices</button>
      <button class="tab-btn" onclick="window.showTab('events')"><span class="tab-icon">🕒</span> Live Events</button>
    </aside>

    <main class="main">
      <!-- ENROLLMENT TAB -->
      <div id="enroll" class="tab-content active">
        <div class="page-title">Enroll a Student</div>
        <div class="page-sub">Photos are processed centrally and reach every bus on their next sync.</div>

        <form id="enrollForm">
          <div class="card">
            <h3>Student Details</h3>
            <div class="form-grid">
              <div class="form-group">
                <label>Child ID</label>
                <input type="text" name="child_id" placeholder="e.g. child_001" required>
              </div>
              <div class="form-group">
                <label>Full Name</label>
                <input type="text" name="name" placeholder="e.g. John Doe" required>
              </div>
              <div class="form-group">
                <label>Assigned Bus ID</label>
                <input type="text" name="bus_id" placeholder="e.g. bus_14" required>
              </div>
              <div class="form-group">
                <label>Pickup Stop ID</label>
                <input type="text" name="pickup_stop_id" placeholder="e.g. stop_1" required>
              </div>
              <div class="form-group">
                <label>Drop Stop ID</label>
                <input type="text" name="drop_stop_id" placeholder="e.g. stop_2" required>
              </div>
              <div class="form-group">
                <label>Twin/Sibling Group (optional)</label>
                <input type="text" name="twin_group" placeholder="Leave blank if none">
              </div>
            </div>
          </div>

          <div class="card">
            <h3>📷 Capture Photos <span class="pill">Need 3-5</span></h3>
            <video id="camera" playsinline></video>
            <canvas id="canvas"></canvas>
            <div>
              <button type="button" onclick="window.startCamera()">Start Camera</button>
              <button type="button" onclick="window.capturePhoto()" id="captureBtn" class="btn-secondary" disabled>Capture Photo</button>
              <button type="button" onclick="window.stopCamera()" class="btn-secondary">Stop Camera</button>
            </div>
            <div class="photo-grid" id="photoGrid"></div>
            
            <hr style="margin: 20px 0; border: none; border-top: 1px solid var(--border);">
            <h3>Or Upload Files Instead</h3>
            <div class="form-group">
              <input type="file" id="photoUpload" accept="image/*" multiple style="padding: 8px;">
            </div>
            <button type="button" onclick="window.processUploadedFiles()">Process Uploaded Photos</button>
          </div>

          <div id="enrollStatus"></div>
          <button type="submit">Enroll Student</button>
          <button type="button" onclick="window.clearPhotos()" class="btn-secondary">Clear Photos</button>
        </form>
      </div>

      <!-- STUDENTS TAB -->
      <div id="students" class="tab-content">
        <div class="page-title">All Students</div>
        <div class="page-sub">Every enrolled student across the fleet.</div>
        <div class="card">
          <input type="text" id="searchBox" class="search-input" placeholder="Search by name or ID...">
          <table>
            <thead>
              <tr><th>ID</th><th>Name</th><th>Bus</th><th>Pickup</th><th>Drop</th><th style="text-align:center;">Photos</th></tr>
            </thead>
            <tbody id="studentsList">
              <tr><td colspan="6" class="empty-state">Loading...</td></tr>
            </tbody>
          </table>
        </div>
        <button onclick="window.loadStudents()" class="btn-secondary">Refresh</button>
      </div>

      <!-- DEVICES TAB -->
      <div id="devices" class="tab-content">
        <div class="page-title">Connected Devices</div>
        <div class="page-sub">Each bus's edge device, live.</div>
        <div class="card" id="devicesList"><p class="empty-state">Loading devices...</p></div>
        <button onclick="window.loadDevices()" class="btn-secondary">Refresh</button>
      </div>

      <!-- EVENTS TAB -->
      <div id="events" class="tab-content">
        <div class="page-title">Live Events</div>
        <div class="page-sub">Pickup and drop confirmations as they happen.</div>
        <div class="card" id="eventsList"><p class="empty-state">Loading events...</p></div>
        <button onclick="window.loadEvents()" class="btn-secondary">Refresh</button>
      </div>
    </main>
  </div>

  <script>
    let photos = [];
    let stream = null;
    
    window.startCamera = async function() {
      try {
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
          alert('Camera access requires HTTPS or localhost');
          return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          alert('Camera not supported');
          return;
        }
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
        document.getElementById('camera').srcObject = stream;
        document.getElementById('captureBtn').disabled = false;
      } catch (err) {
        alert('Camera error: ' + err.message);
      }
    };
    
    window.stopCamera = function() {
      if (stream) {
        stream.getTracks().forEach(t => t.stop());
        document.getElementById('camera').srcObject = null;
        document.getElementById('captureBtn').disabled = true;
      }
    };
    
    window.capturePhoto = function() {
      const video = document.getElementById('camera');
      const canvas = document.getElementById('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);
      const b64 = canvas.toDataURL('image/jpeg').split(',')[1];
      photos.push(b64);
      const div = document.createElement('div');
      div.className = 'photo-thumb';
      const img = document.createElement('img');
      img.src = 'data:image/jpeg;base64,' + b64;
      div.appendChild(img);
      const btn = document.createElement('button');
      btn.className = 'remove';
      btn.type = 'button';
      btn.textContent = '×';
      btn.onclick = (e) => { e.preventDefault(); photos.splice(photos.indexOf(b64), 1); div.remove(); };
      div.appendChild(btn);
      document.getElementById('photoGrid').appendChild(div);
    };
    
    window.clearPhotos = function() {
      photos = [];
      document.getElementById('photoGrid').innerHTML = '';
    };
    
    window.processUploadedFiles = function() {
      const fileInput = document.getElementById('photoUpload');
      if (fileInput.files.length === 0) {
        alert('Please select files first');
        return;
      }
      for (let file of fileInput.files) {
        const reader = new FileReader();
        reader.onload = function(e) {
          const b64 = e.target.result.split(',')[1];
          photos.push(b64);
          const div = document.createElement('div');
          div.className = 'photo-thumb';
          const img = document.createElement('img');
          img.src = e.target.result;
          div.appendChild(img);
          const btn = document.createElement('button');
          btn.className = 'remove';
          btn.type = 'button';
          btn.textContent = '×';
          btn.onclick = (evt) => { evt.preventDefault(); photos.splice(photos.indexOf(b64), 1); div.remove(); };
          div.appendChild(btn);
          document.getElementById('photoGrid').appendChild(div);
        };
        reader.readAsDataURL(file);
      }
    };
    
    window.showTab = function(name) {
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById(name).classList.add('active');
      event.target.classList.add('active');
      if (name === 'students') window.loadStudents();
      else if (name === 'devices') window.loadDevices();
      else if (name === 'events') window.loadEvents();
    };
    
    window.loadStudents = async function() {
      try {
        const resp = await fetch('/api/students');
        const students = await resp.json();
        const tbody = document.getElementById('studentsList');
        if (students.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="padding: 20px; text-align: center;">No students enrolled yet.</td></tr>';
          return;
        }
        const html = students.map((s, idx) => `
          <tr style="background: ${idx % 2 === 0 ? '#fff' : '#fafafa'};">
            <td><code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">${s.child_id}</code></td>
            <td><strong>${s.name}</strong></td>
            <td>${s.assigned_bus_id || '-'}</td>
            <td>${s.pickup_stop_id || '-'}</td>
            <td>${s.drop_stop_id || '-'}</td>
            <td style="text-align: center;"><span style="background: #e3f2fd; padding: 2px 8px; border-radius: 12px; font-size: 12px;">${s.encoding_count}</span></td>
          </tr>
        `).join('');
        tbody.innerHTML = html;
      } catch (e) {
        document.getElementById('studentsList').innerHTML = '<tr><td colspan="6" style="color: red;">Error: ' + e.message + '</td></tr>';
      }
    };
    
    window.loadDevices = async function() {
      try {
        const resp = await fetch('/api/devices');
        const devices = await resp.json();
        const html = devices.map(d => `
          <div class="device-item">
            <div><strong>${d.bus_id}</strong><br><small>${d.last_heartbeat ? new Date(d.last_heartbeat).toLocaleString() : 'Never'}</small></div>
            <div class="device-status ${d.status}">${d.status.toUpperCase()}</div>
          </div>
        `).join('');
        document.getElementById('devicesList').innerHTML = html || '<p>No devices</p>';
      } catch (e) {
        document.getElementById('devicesList').innerHTML = '<p style="color:red;">Error: ' + e.message + '</p>';
      }
    };
    
    window.loadEvents = async function() {
      try {
        const resp = await fetch('/api/live');
        const events = await resp.json();
        const html = events.slice(0, 20).map(e => `
          <div class="event-item">
            <div class="event-header">
              <div><strong>${e.child_id}</strong> <span class="event-type ${e.event_type}">${e.event_type}</span></div>
            </div>
            <div style="font-size: 14px; color: #666;">Bus: ${e.bus_id} | Confidence: ${e.confidence ? e.confidence.toFixed(3) : 'N/A'}</div>
            <div class="event-time">${new Date(e.timestamp).toLocaleString()}</div>
          </div>
        `).join('');
        document.getElementById('eventsList').innerHTML = html || '<p>No events</p>';
      } catch (e) {
        document.getElementById('eventsList').innerHTML = '<p style="color:red;">Error: ' + e.message + '</p>';
      }
    };
    
    document.getElementById('enrollForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const statusEl = document.getElementById('enrollStatus');
      if (photos.length < 3) {
        statusEl.className = 'status error';
        statusEl.textContent = 'Need 3+ photos';
        return;
      }
      const formData = new FormData(e.target);
      const payload = {
        child_id: formData.get('child_id'),
        name: formData.get('name'),
        bus_id: formData.get('bus_id'),
        pickup_stop_id: formData.get('pickup_stop_id'),
        drop_stop_id: formData.get('drop_stop_id'),
        twin_group: formData.get('twin_group') || null,
        photos: photos
      };
      statusEl.className = 'status info';
      statusEl.textContent = 'Processing...';
      try {
        const resp = await fetch('/api/enroll/centralized', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await resp.json();
        if (resp.ok) {
          statusEl.className = 'status success';
          statusEl.textContent = data.message;
          window.clearPhotos();
          e.target.reset();
          window.loadStudents();
        } else {
          statusEl.className = 'status error';
          statusEl.textContent = 'Error: ' + data.message;
        }
      } catch (err) {
        statusEl.className = 'status error';
        statusEl.textContent = 'Error: ' + err.message;
      }
    });
    
    const searchBox = document.getElementById('searchBox');
    if (searchBox) {
      searchBox.addEventListener('keyup', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('#studentsList tr').forEach(row => {
          row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
        });
      });
    }
    
    setInterval(() => {
      const active = document.querySelector('.tab-content.active');
      if (!active) return;
      const id = active.id;
      if (id === 'devices') window.loadDevices();
      else if (id === 'events') window.loadEvents();
    }, 5000);
  </script>
</body>
</html>
"""


# ---- Centralized Enrollment (browser uploads photos to backend) ----

@app.post("/api/enroll/centralized")
def centralized_enroll(data: CentralEnrollmentIn):
    """
    Centralized enrollment: browser sends base64 photos to the backend, which
    forwards them to face_processor.py running on the Pi (NOT processed here -
    the backend never imports face_recognition/dlib, avoiding the Windows dlib
    install problem entirely). The Pi does quality checks + encoding and returns
    the result; the backend just stores it and every device's next sync picks it up.
    """
    if not data.photos:
        raise HTTPException(400, "No photos provided")

    try:
        resp = requests.post(f"{FACE_PROCESSOR_URL}/encode", json={"photos": data.photos}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"status": "error",
                     "message": f"Could not reach face processor at {FACE_PROCESSOR_URL} "
                                f"(is face_processor.py running on the Pi?): {e}"},
        )

    good_encodings = result.get("encodings", [])
    rejections = result.get("rejections", [])

    if not good_encodings:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"No usable photos. Rejections: {rejections}"},
        )

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


# ---- Student Management CRUD API (centralized on backend) ----

class StudentUpdate(BaseModel):
    """Update student info (NOT encodings - those stay)."""
    name: str | None = None
    assigned_bus_id: str | None = None
    pickup_stop_id: str | None = None
    drop_stop_id: str | None = None
    twin_group: str | None = None


@app.get("/api/students")
def list_students():
    """List all students with summary info."""
    try:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
        conn.close()
        
        students = []
        for r in rows:
            try:
                encodings_list = json.loads(r["encodings"])
                num_encodings = len(encodings_list) if isinstance(encodings_list, list) else 1
            except:
                num_encodings = 0
            
            students.append({
                "child_id": r["child_id"],
                "name": r["name"],
                "assigned_bus_id": r["assigned_bus_id"],
                "pickup_stop_id": r["pickup_stop_id"],
                "drop_stop_id": r["drop_stop_id"],
                "twin_group": r["twin_group"],
                "num_encodings": num_encodings,
            })
        
        return {
            "total": len(students),
            "students": students
        }
    except Exception as e:
        print(f"[ERROR] list_students failed: {e}")
        return {
            "total": 0,
            "students": [],
            "error": str(e)
        }


@app.get("/api/students/{child_id}")
def get_student_detail(child_id: str):
    """Get full details for one student."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE child_id = ?", (child_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get current status from events
    conn = get_conn()
    last_event = conn.execute(
        "SELECT event_type FROM events WHERE child_id = ? ORDER BY timestamp DESC LIMIT 1",
        (child_id,)
    ).fetchone()
    conn.close()
    
    last_status = last_event["event_type"] if last_event else "NOT_PICKED_UP"
    
    return {
        "child_id": row["child_id"],
        "name": row["name"],
        "assigned_bus_id": row["assigned_bus_id"],
        "pickup_stop_id": row["pickup_stop_id"],
        "drop_stop_id": row["drop_stop_id"],
        "twin_group": row["twin_group"],
        "num_encodings": len(json.loads(row["encodings"])),
        "last_status": last_status,
    }


@app.post("/api/students/{child_id}")
def update_student(child_id: str, data: StudentUpdate):
    """Update student info (name, stops, bus - NOT encodings)."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE child_id = ?", (child_id,)).fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Keep existing encodings, update only specified fields
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.assigned_bus_id is not None:
        updates["assigned_bus_id"] = data.assigned_bus_id
    if data.pickup_stop_id is not None:
        updates["pickup_stop_id"] = data.pickup_stop_id
    if data.drop_stop_id is not None:
        updates["drop_stop_id"] = data.drop_stop_id
    if data.twin_group is not None:
        updates["twin_group"] = data.twin_group
    
    if not updates:
        conn.close()
        return {"status": "no_changes"}
    
    # Build UPDATE query dynamically
    set_clauses = ", ".join([f"{k}=?" for k in updates.keys()])
    values = list(updates.values()) + [child_id]
    
    conn.execute(f"UPDATE students SET {set_clauses} WHERE child_id = ?", values)
    conn.commit()
    conn.close()
    
    return {"status": "updated", "child_id": child_id, "fields": list(updates.keys())}


@app.delete("/api/students/{child_id}")
def delete_student(child_id: str):
    """Delete a student from the roster."""
    conn = get_conn()
    
    # Check if student exists
    row = conn.execute("SELECT * FROM students WHERE child_id = ?", (child_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Delete student (events remain for audit trail)
    conn.execute("DELETE FROM students WHERE child_id = ?", (child_id,))
    conn.commit()
    conn.close()
    
    return {"status": "deleted", "child_id": child_id}


@app.delete("/api/students")
def delete_all_students(confirm: str = None):
    """DELETE ALL STUDENTS - DANGEROUS! Requires confirm=yes parameter."""
    if confirm != "yes":
        raise HTTPException(
            status_code=400,
            detail="To delete ALL students, pass ?confirm=yes parameter"
        )
    
    conn = get_conn()
    conn.execute("DELETE FROM students")
    conn.commit()
    count = conn.total_changes
    conn.close()
    
    return {
        "status": "deleted_all",
        "students_deleted": count,
        "message": "All students deleted. Pi devices will have empty roster on next sync (30s)."
    }


@app.get("/api/export")
def export_students():
    """Export all students as JSON (backup/transfer)."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    
    students = []
    for r in rows:
        students.append({
            "child_id": r["child_id"],
            "name": r["name"],
            "encodings": json.loads(r["encodings"]),
            "assigned_bus_id": r["assigned_bus_id"],
            "pickup_stop_id": r["pickup_stop_id"],
            "drop_stop_id": r["drop_stop_id"],
            "twin_group": r["twin_group"],
        })
    
    return {
        "exported_at": datetime.datetime.now().isoformat(),
        "total_students": len(students),
        "students": students
    }


@app.get("/api/students/health/ping")
def students_health():
    """Health check endpoint."""
    return {"status": "ok"}


# ---- Student Management Dashboard (Web UI on Backend) ----

@app.get("/management")
def management_dashboard():
    """Student management dashboard - view, edit, delete students."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Management - Bus System</title>
        <style>
            * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; min-height: 100vh; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
            h1 { color: #333; margin-top: 0; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
            .controls { margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap; }
            button { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: 600; transition: all 0.3s; }
            button.primary { background: #667eea; color: white; }
            button.primary:hover { background: #5568d3; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102,126,234,0.4); }
            button.danger { background: #ff6b6b; color: white; }
            button.danger:hover { background: #ff5252; }
            button.success { background: #51cf66; color: white; }
            button.success:hover { background: #40c057; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; }
            .stat h3 { margin: 0 0 5px 0; opacity: 0.9; font-size: 14px; }
            .stat .value { font-size: 28px; font-weight: bold; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th { background: #667eea; color: white; padding: 15px; text-align: left; font-weight: 600; }
            td { padding: 12px 15px; border-bottom: 1px solid #eee; }
            tr:hover { background: #f9f9f9; }
            .actions { display: flex; gap: 5px; }
            .actions button { padding: 6px 12px; font-size: 12px; }
            .empty { text-align: center; padding: 40px; color: #999; }
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
            .modal.show { display: flex; }
            .modal-content { background: white; padding: 30px; border-radius: 8px; width: 90%; max-width: 500px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }
            .modal h2 { margin-top: 0; color: #333; }
            .form-group { margin-bottom: 15px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; }
            .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            .form-group input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
            .modal-buttons { display: flex; gap: 10px; margin-top: 20px; }
            .badge { display: inline-block; padding: 4px 8px; background: #e3f2fd; color: #1976d2; border-radius: 3px; font-size: 12px; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👥 Student Management Dashboard</h1>
            
            <div class="stats">
                <div class="stat">
                    <h3>Total Students</h3>
                    <div class="value" id="total">0</div>
                </div>
                <div class="stat">
                    <h3>Enrolled Today</h3>
                    <div class="value" id="today">0</div>
                </div>
                <div class="stat">
                    <h3>System Status</h3>
                    <div class="value" id="status" style="font-size: 14px; color: #51cf66;">🟢 LIVE</div>
                </div>
            </div>
            
            <div class="controls">
                <button class="success" onclick="exportStudents()">📥 Export All</button>
                <button class="primary" onclick="reloadStudents()">🔄 Refresh</button>
            </div>
            
            <table id="students-table">
                <thead>
                    <tr>
                        <th>Student ID</th>
                        <th>Name</th>
                        <th>Bus</th>
                        <th>Pickup Stop</th>
                        <th>Drop Stop</th>
                        <th>Photos</th>
                        <th>Last Event</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="students-body">
                    <tr><td colspan="8" class="empty">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Edit Modal -->
        <div class="modal" id="edit-modal">
            <div class="modal-content">
                <h2>Edit Student</h2>
                <div class="form-group">
                    <label>Student ID</label>
                    <input type="text" id="edit-id" disabled>
                </div>
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" id="edit-name">
                </div>
                <div class="form-group">
                    <label>Bus ID</label>
                    <input type="text" id="edit-bus">
                </div>
                <div class="form-group">
                    <label>Pickup Stop</label>
                    <input type="text" id="edit-pickup">
                </div>
                <div class="form-group">
                    <label>Drop Stop</label>
                    <input type="text" id="edit-drop">
                </div>
                <div class="modal-buttons">
                    <button class="primary" onclick="saveChanges()">Save</button>
                    <button onclick="closeModal()" style="background: #e0e0e0;">Cancel</button>
                </div>
            </div>
        </div>

        <script>
            let currentEditId = null;

            async function loadStudents() {
                try {
                    const res = await fetch('/api/students');
                    if (!res.ok) {
                        throw new Error(`API returned ${res.status}`);
                    }
                    const data = await res.json();
                    
                    // Handle case where data structure is wrong
                    if (!data || typeof data.total === 'undefined' || !Array.isArray(data.students)) {
                        console.error('Unexpected API response:', data);
                        document.getElementById('students-body').innerHTML = 
                            '<tr><td colspan="8" class="empty">Error loading students. Check console.</td></tr>';
                        return;
                    }
                    
                    document.getElementById('total').textContent = data.total;
                    
                    const body = document.getElementById('students-body');
                    if (!data.students || data.students.length === 0) {
                        body.innerHTML = '<tr><td colspan="8" class="empty">No students enrolled yet. Use the enrollment dashboard to add students.</td></tr>';
                        return;
                    }
                    
                    body.innerHTML = data.students.map(s => `
                        <tr>
                            <td><code>${s.child_id}</code></td>
                            <td><strong>${s.name}</strong></td>
                            <td>${s.assigned_bus_id || '—'}</td>
                            <td>${s.pickup_stop_id || '—'}</td>
                            <td>${s.drop_stop_id || '—'}</td>
                            <td><span class="badge">${s.num_encodings} photos</span></td>
                            <td>—</td>
                            <td>
                                <div class="actions">
                                    <button class="primary" onclick="editStudent('${s.child_id}')">Edit</button>
                                    <button class="danger" onclick="deleteStudent('${s.child_id}')">Delete</button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                } catch (e) {
                    console.error('Error loading students:', e);
                    document.getElementById('students-body').innerHTML = 
                        '<tr><td colspan="8" class="empty">Failed to load students: ' + e.message + '</td></tr>';
                }
            }

            async function editStudent(child_id) {
                try {
                    const res = await fetch(`/api/students/${child_id}`);
                    const s = await res.json();
                    
                    currentEditId = child_id;
                    document.getElementById('edit-id').value = s.child_id;
                    document.getElementById('edit-name').value = s.name;
                    document.getElementById('edit-bus').value = s.assigned_bus_id || '';
                    document.getElementById('edit-pickup').value = s.pickup_stop_id || '';
                    document.getElementById('edit-drop').value = s.drop_stop_id || '';
                    
                    document.getElementById('edit-modal').classList.add('show');
                } catch (e) {
                    console.error('Error:', e);
                    alert('Failed to load student');
                }
            }

            async function saveChanges() {
                const data = {
                    name: document.getElementById('edit-name').value,
                    assigned_bus_id: document.getElementById('edit-bus').value,
                    pickup_stop_id: document.getElementById('edit-pickup').value,
                    drop_stop_id: document.getElementById('edit-drop').value,
                };
                
                try {
                    const res = await fetch(`/api/students/${currentEditId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (res.ok) {
                        alert('✓ Student updated');
                        closeModal();
                        loadStudents();
                    } else {
                        alert('Failed to update student');
                    }
                } catch (e) {
                    console.error('Error:', e);
                    alert('Error updating student');
                }
            }

            async function deleteStudent(child_id) {
                if (!confirm(`Are you sure? Delete "${child_id}"? This cannot be undone.`)) return;
                
                try {
                    const res = await fetch(`/api/students/${child_id}`, { method: 'DELETE' });
                    if (res.ok) {
                        alert('✓ Student deleted');
                        loadStudents();
                    } else {
                        alert('Failed to delete student');
                    }
                } catch (e) {
                    console.error('Error:', e);
                    alert('Error deleting student');
                }
            }

            async function exportStudents() {
                try {
                    const res = await fetch('/api/export');
                    const data = await res.json();
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `students_${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                } catch (e) {
                    console.error('Error:', e);
                    alert('Error exporting data');
                }
            }

            function closeModal() {
                document.getElementById('edit-modal').classList.remove('show');
            }

            function reloadStudents() {
                loadStudents();
            }

            // Auto-load
            loadStudents();
            setInterval(loadStudents, 10000); // Refresh every 10 seconds
        </script>
    </body>
    </html>
    """)
