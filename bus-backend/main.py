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


@app.get("/api/students")
def get_all_students():
    """Get all enrolled students."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    students = []
    for r in rows:
        students.append({
            "child_id": r["child_id"],
            "name": r["name"],
            "assigned_bus_id": r["assigned_bus_id"],
            "pickup_stop_id": r["pickup_stop_id"],
            "drop_stop_id": r["drop_stop_id"],
            "twin_group": r["twin_group"],
            "encoding_count": len(json.loads(r["encodings"]))
        })
    return students


@app.get("/")
def root():
    return {"status": "Bus backend running", "docs": "/docs"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Live enrollment dashboard with device tracking and event feed."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>School Bus - Central Dashboard</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #1a3a52; margin-bottom: 30px; text-align: center; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #ddd; }
        .tab-btn { padding: 12px 24px; background: none; border: none; cursor: pointer; font-size: 16px; color: #666; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #1a3a52; border-bottom-color: #1a3a52; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
        input[type=text], select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        
        .camera-section { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        video { width: 100%; max-width: 500px; border: 2px solid #ddd; border-radius: 4px; margin-bottom: 15px; display: block; }
        canvas { display: none; }
        
        .photo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
        .photo-thumb { position: relative; aspect-ratio: 1; border-radius: 4px; overflow: hidden; border: 2px solid #e0e0e0; }
        .photo-thumb img { width: 100%; height: 100%; object-fit: cover; }
        .photo-thumb .remove { position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.7); color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; font-size: 18px; }
        
        button { padding: 12px 24px; background: #1a3a52; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-right: 10px; margin-bottom: 10px; }
        button:hover { background: #0f2841; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .btn-secondary { background: #666; }
        .btn-secondary:hover { background: #555; }
        
        .status { padding: 15px; border-radius: 4px; margin: 15px 0; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        
        .device-list { background: #fff; padding: 20px; border-radius: 8px; }
        .device-item { padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .device-item:last-child { border-bottom: none; }
        .device-status { padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; }
        .device-status.online { background: #d4edda; color: #155724; }
        .device-status.offline { background: #f8d7da; color: #721c24; }
        
        .event-list { background: #fff; padding: 20px; border-radius: 8px; }
        .event-item { padding: 15px; border-bottom: 1px solid #eee; }
        .event-item:last-child { border-bottom: none; }
        .event-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
        .event-type { font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .event-type.PICKED_UP { background: #d4edda; color: #155724; }
        .event-type.DROPPED { background: #cfe2ff; color: #084298; }
        .event-time { color: #666; font-size: 14px; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; font-weight: 600; color: #333; }
        tr:hover { background: #fafafa; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🚌 School Bus Central Dashboard</h1>
        
        <div class="tabs">
          <button class="tab-btn active" onclick="showTab('enroll')">Enroll Student</button>
          <button class="tab-btn" onclick="showTab('students')">All Students</button>
          <button class="tab-btn" onclick="showTab('devices')">Connected Devices</button>
          <button class="tab-btn" onclick="showTab('events')">Live Events</button>
        </div>
        
        <!-- ENROLLMENT TAB -->
        <div id="enroll" class="tab-content active">
          <form id="enrollForm" style="background: #fff; padding: 20px; border-radius: 8px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
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
            
            <div class="camera-section">
              <h3>📷 Capture Photos (Need 3-5)</h3>
              <video id="camera" playsinline></video>
              <canvas id="canvas"></canvas>
              <div>
                <button type="button" onclick="startCamera()">Start Camera</button>
                <button type="button" onclick="capturePhoto()" id="captureBtn" disabled>Capture Photo</button>
                <button type="button" onclick="stopCamera()" class="btn-secondary">Stop Camera</button>
              </div>
              <div class="photo-grid" id="photoGrid"></div>
            </div>
            
            <div id="enrollStatus"></div>
            
            <button type="submit">Enroll Student</button>
            <button type="button" onclick="clearPhotos()" class="btn-secondary">Clear Photos</button>
          </form>
        </div>
        
        <!-- STUDENTS TAB -->
        <div id="students" class="tab-content">
          <div style="background: #fff; padding: 20px; border-radius: 8px;">
            <input type="text" id="searchBox" placeholder="Search by name or ID..." style="margin-bottom: 15px; width: 300px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
              <thead style="background: #f5f5f5;">
                <tr>
                  <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">ID</th>
                  <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Name</th>
                  <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Bus</th>
                  <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Pickup</th>
                  <th style="padding: 12px; text-align: left; border-bottom: 2px solid #ddd;">Drop</th>
                  <th style="padding: 12px; text-align: center; border-bottom: 2px solid #ddd;">Photos</th>
                </tr>
              </thead>
              <tbody id="studentsList">
                <tr><td colspan="6" style="padding: 20px; text-align: center; color: #999;">Loading...</td></tr>
              </tbody>
            </table>
          </div>
          <button onclick="loadStudents()" style="margin-top: 20px;">Refresh</button>
        </div>
        
        <!-- DEVICES TAB -->
        <div id="devices" class="tab-content">
          <div class="device-list" id="devicesList">
            <p>Loading devices...</p>
          </div>
          <button onclick="loadDevices()" style="margin-top: 20px;">Refresh</button>
        </div>
        
        <!-- EVENTS TAB -->
        <div id="events" class="tab-content">
          <div class="event-list" id="eventsList">
            <p>Loading events...</p>
          </div>
          <button onclick="loadEvents()" style="margin-top: 20px;">Refresh</button>
        </div>
      </div>

      <script>
        let photos = [];
        let stream = null;
        
        async function startCamera() {
          try {
            // Check if we're on HTTPS or localhost for camera access
            if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
              alert('Camera access requires HTTPS. Please access the dashboard via HTTPS or localhost.');
              return;
            }
            
            // Check if mediaDevices is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
              alert('Camera not supported on this browser. Try Chrome, Firefox, or Edge.');
              return;
            }
            
            stream = await navigator.mediaDevices.getUserMedia({ 
              video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } } 
            });
            document.getElementById('camera').srcObject = stream;
            document.getElementById('captureBtn').disabled = false;
          } catch (err) {
            alert('Camera access denied: ' + err.message + '\n\nMake sure:\n1. You gave browser permission\n2. Using HTTPS or localhost\n3. Camera is not in use by another app');
          }
        }
        
        function stopCamera() {
          if (stream) {
            stream.getTracks().forEach(t => t.stop());
            document.getElementById('camera').srcObject = null;
            document.getElementById('captureBtn').disabled = true;
          }
        }
        
        function capturePhoto() {
          const video = document.getElementById('camera');
          const canvas = document.getElementById('canvas');
          const ctx = canvas.getContext('2d');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);
          
          const b64 = canvas.toDataURL('image/jpeg').split(',')[1];
          photos.push(b64);
          
          // Show thumbnail
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
        }
        
        function clearPhotos() {
          photos = [];
          document.getElementById('photoGrid').innerHTML = '';
        }
        
        function showTab(name) {
          document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
          document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
          document.getElementById(name).classList.add('active');
          event.target.classList.add('active');
          
          if (name === 'students') loadStudents();
          else if (name === 'devices') loadDevices();
          else if (name === 'events') loadEvents();
        }
        
        async function loadStudents() {
          try {
            const resp = await fetch('/api/students');
            const students = await resp.json();
            
            const tbody = document.getElementById('studentsList');
            if (students.length === 0) {
              tbody.innerHTML = '<tr><td colspan="6" style="padding: 20px; text-align: center; color: #999;">No students enrolled yet.</td></tr>';
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
            document.getElementById('studentsList').innerHTML = '<tr><td colspan="6" style="padding: 20px; color: red;">Error loading students</td></tr>';
          }
        }
        
        async function loadDevices() {
          try {
            const resp = await fetch('/api/devices');
            const devices = await resp.json();
            const html = devices.map(d => `
              <div class="device-item">
                <div>
                  <strong>${d.bus_id}</strong><br>
                  <small>${d.last_heartbeat ? new Date(d.last_heartbeat).toLocaleString() : 'Never'}</small>
                </div>
                <div class="device-status ${d.status}">${d.status.toUpperCase()}</div>
              </div>
            `).join('');
            document.getElementById('devicesList').innerHTML = html || '<p>No devices connected yet.</p>';
          } catch (e) {
            document.getElementById('devicesList').innerHTML = '<p style="color:red;">Error loading devices</p>';
          }
        }
        
        async function loadEvents() {
          try {
            const resp = await fetch('/api/live');
            const events = await resp.json();
            const html = events.slice(0, 20).map(e => `
              <div class="event-item">
                <div class="event-header">
                  <div>
                    <strong>${e.child_id}</strong><span class="event-type ${e.event_type}">${e.event_type}</span>
                  </div>
                </div>
                <div style="font-size: 14px; color: #666;">
                  Bus: ${e.bus_id} | Confidence: ${e.confidence ? e.confidence.toFixed(3) : 'N/A'}
                </div>
                <div class="event-time">${new Date(e.timestamp).toLocaleString()}</div>
              </div>
            `).join('');
            document.getElementById('eventsList').innerHTML = html || '<p>No events yet.</p>';
          } catch (e) {
            document.getElementById('eventsList').innerHTML = '<p style="color:red;">Error loading events</p>';
          }
        }
        
        document.getElementById('enrollForm').addEventListener('submit', async (e) => {
          e.preventDefault();
          const statusEl = document.getElementById('enrollStatus');
          
          if (photos.length < 3) {
            statusEl.className = 'status error';
            statusEl.textContent = 'Please capture at least 3 photos';
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
          statusEl.textContent = 'Processing photos and enrolling... This may take 30-60 seconds.';
          
          try {
            const resp = await fetch('/api/enroll/centralized', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
            const data = await resp.json();
            
            if (resp.ok) {
              statusEl.className = 'status success';
              statusEl.textContent = data.message;
              clearPhotos();
              e.target.reset();
              // Reload students table
              loadStudents();
            } else {
              statusEl.className = 'status error';
              statusEl.textContent = 'Error: ' + data.message;
            }
          } catch (err) {
            statusEl.className = 'status error';
            statusEl.textContent = 'Error: ' + err.message;
          }
        });
        
        // Add search functionality
        document.getElementById('searchBox').addEventListener('keyup', (e) => {
          const query = e.target.value.toLowerCase();
          document.querySelectorAll('#studentsList tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(query) ? '' : 'none';
          });
        });
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
          const active = document.querySelector('.tab-content.active');
          if (!active) return;
          const id = active.id;
          if (id === 'devices') loadDevices();
          else if (id === 'events') loadEvents();
        }, 5000);
      </script>
    </body>
    </html>
    """
    return html


# ---- Centralized Enrollment (browser uploads photos to backend) ----

@app.post("/api/enroll/centralized")
def centralized_enroll(data: CentralEnrollmentIn):
    """
    Centralized enrollment: browser sends base64 photos to backend.
    Backend processes them, generates encodings, stores student, syncs to all devices.
    """
    if not data.photos:
        raise HTTPException(400, "No photos provided")
    
    good_encodings = []
    rejections = []
    
    for i, b64_photo in enumerate(data.photos):
        # Decode base64 to image
        image = base64_to_cv2(b64_photo)
        if image is None:
            rejections.append(f"Photo {i+1}: Invalid image data")
            continue
        
        # Quality check
        ok, msg = quality_check_image(image)
        if not ok:
            rejections.append(f"Photo {i+1}: {msg}")
            continue
        
        # Generate encoding
        encoding, err = get_encoding_from_image(image)
        if err:
            rejections.append(f"Photo {i+1}: {err}")
            continue
        
        good_encodings.append(encoding)
    
    if not good_encodings:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"No usable photos. Rejections: {rejections}"
            }
        )
    
    # Store student in database
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
