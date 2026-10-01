"""
HTML dashboards for enrollment and student management.
Serves as a centralized UI for staff to manage the system.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboards"])


@router.get("/", response_class=HTMLResponse)
def root_dashboard():
    """Root endpoint - links to dashboards."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Bus Central - Welcome</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; }
        h1 { color: #333; margin: 0 0 10px 0; }
        .subtitle { color: #666; margin-bottom: 40px; }
        .links { display: flex; flex-direction: column; gap: 15px; }
        a { padding: 15px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.2s; }
        a:hover { background: #764ba2; transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
        .docs { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }
        .docs a { background: none; color: #667eea; padding: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚌 Bus Central Backend</h1>
        <p class="subtitle">Centralized student enrollment and fleet management</p>
        
        <div class="links">
            <a href="/dashboard">📊 Enrollment Dashboard</a>
            <a href="/management">👥 Student Management</a>
            <a href="/docs">📖 API Documentation</a>
        </div>
        
        <div class="docs">
            <p><strong>Endpoints:</strong> POST /api/enroll, GET /api/bus/{bus_id}/roster, etc.</p>
        </div>
    </div>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def enrollment_dashboard():
    """Enrollment dashboard with camera capture and photo upload."""
    # This is the enrollment dashboard HTML
    # (truncated for length - it's the same as in the original main.py)
    return """<!DOCTYPE html>
<html>
<head>
    <title>School Bus - Central Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --navy: #0f2540; --accent: #2f6fed; --green: #1fa971; --green-bg: #e8f9f1; --red: #e5484d; --red-bg: #fdecec; --blue-bg: #eaf1ff; --blue-text: #2f6fed; --ink: #0f172a; --muted: #64748b; --border: #e6eaf0; --bg: #f4f6fb; --card: #ffffff; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--ink); }
        .shell { display: flex; min-height: 100vh; }
        .sidebar { width: 240px; background: var(--navy); color: #fff; flex-shrink: 0; padding: 24px 0; display: flex; flex-direction: column; }
        .brand { display: flex; align-items: center; gap: 10px; padding: 0 24px 24px; font-weight: 800; font-size: 1.05rem; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px; }
        .tab-btn { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; padding: 12px 24px; background: none; border: none; color: rgba(255,255,255,0.65); font-size: 0.92rem; font-weight: 500; cursor: pointer; border-left: 3px solid transparent; transition: all .15s; }
        .tab-btn:hover { background: rgba(255,255,255,0.05); color: #fff; }
        .tab-btn.active { background: rgba(47,111,237,0.15); color: #fff; border-left-color: var(--accent); }
        .main { flex: 1; padding: 32px 40px; }
        .page-title { font-size: 1.5rem; font-weight: 800; margin-bottom: 4px; }
        .page-sub { color: var(--muted); font-size: 0.92rem; margin-bottom: 28px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 0.82rem; }
        input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.92rem; font-family: inherit; }
        input:focus { outline: none; border-color: var(--accent); }
        button { padding: 10px 20px; background: var(--navy); color: white; border: none; border-radius: 8px; font-size: 0.88rem; font-weight: 600; cursor: pointer; margin-top: 20px; }
        button:hover { background: #16345c; }
        .status { padding: 12px 16px; border-radius: 8px; margin: 14px 0; font-size: 0.88rem; }
        .status.success { background: var(--green-bg); color: #0d7a4f; }
        .status.error { background: var(--red-bg); color: #b3272b; }
        table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
        th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: #fbfcfe; font-weight: 700; color: var(--muted); }
    </style>
</head>
<body>
    <div class="shell">
        <aside class="sidebar">
            <div class="brand">🚌 Bus Central</div>
            <button class="tab-btn active" onclick="showTab('enroll')">➕ Enroll</button>
            <button class="tab-btn" onclick="showTab('students')">🎓 Students</button>
            <button class="tab-btn" onclick="showTab('events')">🕒 Events</button>
        </aside>
        <main class="main">
            <div id="enroll" class="tab-content" style="display: block;">
                <div class="page-title">Enroll a Student</div>
                <div class="page-sub">Upload photos for face recognition enrollment.</div>
                <form id="enrollForm">
                    <div class="card">
                        <div class="form-group"><label>Child ID</label><input type="text" id="childId" required></div>
                        <div class="form-group"><label>Name</label><input type="text" id="name" required></div>
                        <div class="form-group"><label>Bus ID</label><input type="text" id="busId" required></div>
                        <div class="form-group"><label>Pickup Stop</label><input type="text" id="pickupStop" required></div>
                        <div class="form-group"><label>Drop Stop</label><input type="text" id="dropStop" required></div>
                        <div class="form-group"><label>Photos</label><input type="file" id="photos" multiple accept="image/*" required></div>
                        <button type="submit">Enroll</button>
                    </div>
                </form>
                <div id="enrollStatus"></div>
            </div>
            <div id="students" class="tab-content" style="display: none;">
                <div class="page-title">All Students</div>
                <table><thead><tr><th>ID</th><th>Name</th><th>Bus</th></tr></thead><tbody id="studentsList"></tbody></table>
            </div>
            <div id="events" class="tab-content" style="display: none;">
                <div class="page-title">Recent Events</div>
                <table><thead><tr><th>Time</th><th>Student</th><th>Event</th></tr></thead><tbody id="eventsList"></tbody></table>
            </div>
        </main>
    </div>
    <script>
        function showTab(name) {
            document.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(name).style.display = 'block';
            event.target.classList.add('active');
        }
        document.getElementById('enrollForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const files = document.getElementById('photos').files;
            const photos = [];
            for (let file of files) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    photos.push(evt.target.result.split(',')[1]);
                    if (photos.length === files.length) {
                        submitEnroll(photos);
                    }
                };
                reader.readAsDataURL(file);
            }
        });
        function submitEnroll(photos) {
            fetch('/api/enroll/centralized', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    child_id: document.getElementById('childId').value,
                    name: document.getElementById('name').value,
                    bus_id: document.getElementById('busId').value,
                    pickup_stop_id: document.getElementById('pickupStop').value,
                    drop_stop_id: document.getElementById('dropStop').value,
                    photos: photos
                })
            }).then(r => r.json()).then(data => {
                const status = document.getElementById('enrollStatus');
                if (data.status === 'success') {
                    status.className = 'status success';
                    status.textContent = '✓ ' + data.message;
                    document.getElementById('enrollForm').reset();
                } else {
                    status.className = 'status error';
                    status.textContent = '✗ ' + (data.message || 'Enrollment failed');
                }
            }).catch(e => {
                document.getElementById('enrollStatus').className = 'status error';
                document.getElementById('enrollStatus').textContent = '✗ Error: ' + e.message;
            });
        }
    </script>
</body>
</html>
"""


@router.get("/management", response_class=HTMLResponse)
def management_dashboard():
    """Student management dashboard - CRUD operations."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Student Management</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 30px; }
        .controls { margin-bottom: 20px; display: flex; gap: 10px; }
        button { padding: 10px 20px; background: #0f2540; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background: #16345c; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f9f9f9; font-weight: 600; }
        tr:hover { background: #f5f5f5; }
        input { padding: 5px 10px; border: 1px solid #ddd; border-radius: 4px; }
        .status { padding: 10px; margin-top: 20px; border-radius: 6px; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>👥 Student Management</h1>
        <div class="controls">
            <button onclick="loadStudents()">Refresh</button>
            <button onclick="exportCSV()">📥 Export CSV</button>
            <button onclick="deleteAllConfirm()" style="background: #e5484d;">🗑️ Delete All</button>
        </div>
        <table id="studentsTable">
            <thead>
                <tr><th>ID</th><th>Name</th><th>Bus</th><th>Pickup</th><th>Drop</th><th>Photos</th><th>Actions</th></tr>
            </thead>
            <tbody id="studentsList">
                <tr><td colspan="7" style="text-align: center;">Loading...</td></tr>
            </tbody>
        </table>
        <div id="status"></div>
    </div>
    <script>
        async function loadStudents() {
            try {
                const resp = await fetch('/api/students');
                const data = await resp.json();
                const students = data.students || data;  // Handle both formats
                const tbody = document.getElementById('studentsList');
                if (!students || students.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No students enrolled.</td></tr>';
                    return;
                }
                tbody.innerHTML = students.map(s => `
                    <tr>
                        <td><code>${s.child_id}</code></td>
                        <td>${s.name}</td>
                        <td>${s.assigned_bus_id || '-'}</td>
                        <td>${s.pickup_stop_id || '-'}</td>
                        <td>${s.drop_stop_id || '-'}</td>
                        <td>${s.encoding_count || 0}</td>
                        <td><button onclick="deleteStudent('${s.child_id}')" style="background: #e5484d; padding: 5px 10px; font-size: 0.85rem;">Delete</button></td>
                    </tr>
                `).join('');
            } catch (e) {
                document.getElementById('studentsList').innerHTML = '<tr><td colspan="7" style="color: red;">Error: ' + e.message + '</td></tr>';
            }
        }
        function deleteStudent(childId) {
            if (!confirm(`Delete ${childId}?`)) return;
            fetch(`/api/students/${childId}`, { method: 'DELETE' })
                .then(() => { showStatus('Deleted successfully', 'success'); loadStudents(); })
                .catch(e => showStatus('Error: ' + e.message, 'error'));
        }
        function deleteAllConfirm() {
            if (!confirm('Delete ALL students? This cannot be undone!')) return;
            fetch('/api/students?confirm=yes-delete-all', { method: 'DELETE' })
                .then(() => { showStatus('All students deleted', 'success'); loadStudents(); })
                .catch(e => showStatus('Error: ' + e.message, 'error'));
        }
        function exportCSV() {
            window.location.href = '/api/students/export/csv';
        }
        function showStatus(msg, type) {
            const status = document.getElementById('status');
            status.className = `status ${type}`;
            status.textContent = msg;
        }
        loadStudents();
        setInterval(loadStudents, 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>
"""
