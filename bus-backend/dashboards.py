"""
Production-Grade Dashboards for School Bus Face Recognition Fleet.
Includes:
- Root Command Center (/)
- Unified Fleet Operations & Enrollment Dashboard (/dashboard)
- Student & Fleet Management Portal (/management)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboards"])


@router.get("/", response_class=HTMLResponse)
def root_dashboard():
    """Command Center Hub - High-end landing interface."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeBus AI — Fleet & Face Recognition Command Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --surface: #111827;
            --surface-elevated: #1a2234;
            --border: #1f293d;
            --border-light: rgba(255,255,255,0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --primary: #4f46e5;
            --primary-light: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --accent: #06b6d4;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
            background-image: 
                radial-gradient(circle at 15% 20%, rgba(99, 102, 241, 0.12) 0%, transparent 45%),
                radial-gradient(circle at 85% 80%, rgba(6, 182, 212, 0.08) 0%, transparent 45%);
            background-attachment: fixed;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 48px 24px 64px;
        }

        /* Top Bar */
        .top-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 56px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-icon {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, var(--primary) 0%, #8b5cf6 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 8px 16px var(--primary-glow);
        }
        .brand-text h1 {
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #fff 60%, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .brand-text p {
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .live-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 9999px;
            font-size: 0.82rem;
            color: #34d399;
            font-weight: 600;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* Hero */
        .hero {
            text-align: center;
            max-width: 780px;
            margin: 0 auto 56px;
        }
        .hero-badge {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 9999px;
            color: #818cf8;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 16px;
        }
        .hero h2 {
            font-size: 2.8rem;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.03em;
            margin-bottom: 16px;
        }
        .hero p {
            font-size: 1.12rem;
            color: var(--text-secondary);
            font-weight: 400;
        }

        /* Metrics Bar */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 48px;
        }
        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            transition: all 0.25s ease;
        }
        .metric-card:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
            background: var(--surface-elevated);
        }
        .metric-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: rgba(255,255,255,0.04);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .metric-content .val {
            font-size: 1.6rem;
            font-weight: 800;
            color: #fff;
            letter-spacing: -0.02em;
        }
        .metric-content .lbl {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* App Portals Grid */
        .portal-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 48px;
        }
        .portal-card {
            position: relative;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 32px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            text-decoration: none;
            color: inherit;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .portal-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: transparent;
            transition: all 0.3s;
        }
        .portal-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-4px);
            box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
            background: var(--surface-elevated);
        }
        .portal-card.primary::before { background: linear-gradient(90deg, #4f46e5, #06b6d4); }
        .portal-card.emerald::before { background: linear-gradient(90deg, #10b981, #059669); }
        .portal-card.violet::before { background: linear-gradient(90deg, #8b5cf6, #ec4899); }
        .portal-card.amber::before { background: linear-gradient(90deg, #f59e0b, #ef4444); }

        .portal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .portal-badge {
            font-size: 0.72rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-indigo { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
        .badge-green { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .badge-purple { background: rgba(139, 92, 246, 0.15); color: #c084fc; }
        .badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

        .portal-emoji {
            font-size: 32px;
        }
        .portal-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
        }
        .portal-desc {
            font-size: 0.92rem;
            color: var(--text-secondary);
            margin-bottom: 24px;
            line-height: 1.6;
        }
        .portal-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 18px;
            border-top: 1px solid var(--border-light);
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--primary-light);
        }
        .arrow-icon {
            transition: transform 0.2s ease;
        }
        .portal-card:hover .arrow-icon {
            transform: translateX(4px);
        }

        /* System Architecture Strip */
        .system-strip {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
        }
        .strip-col {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .strip-label {
            font-size: 0.78rem;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 700;
        }
        .strip-val {
            font-size: 0.92rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            color: #e2e8f0;
        }

        footer {
            margin-top: 56px;
            text-align: center;
            font-size: 0.82rem;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Navigation -->
        <header class="top-nav">
            <div class="brand">
                <div class="brand-icon">🚌</div>
                <div class="brand-text">
                    <h1>SafeBus Central Hub</h1>
                    <p>Fleet Facial Recognition & Student Safety System</p>
                </div>
            </div>
            <div class="live-status">
                <span class="pulse-dot"></span>
                <span>SYSTEM ONLINE</span>
            </div>
        </header>

        <!-- Hero Section -->
        <section class="hero">
            <span class="hero-badge">Autonomous Edge & Cloud Operations</span>
            <h2>Fleet Safety & Attendance Command Center</h2>
            <p>Real-time passenger verification, edge device sync, and centralized student roster operations for school bus fleets.</p>
        </section>

        <!-- Live Metrics Bar -->
        <section class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon">🎓</div>
                <div class="metric-content">
                    <div class="val" id="metricStudents">--</div>
                    <div class="lbl">Enrolled Students</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🚌</div>
                <div class="metric-content">
                    <div class="val" id="metricBuses">--</div>
                    <div class="lbl">Registered Buses</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-content">
                    <div class="val" id="metricEvents">--</div>
                    <div class="lbl">Recent Events</div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-content">
                    <div class="val" id="metricProcessor">Online</div>
                    <div class="lbl">Face AI Engine</div>
                </div>
            </div>
        </section>

        <!-- Application Portals -->
        <section class="portal-grid">
            <a href="/dashboard" class="portal-card primary">
                <div>
                    <div class="portal-header">
                        <span class="portal-emoji">📊</span>
                        <span class="portal-badge badge-indigo">Primary Control</span>
                    </div>
                    <div class="portal-title">Fleet Operations & Live Feed</div>
                    <div class="portal-desc">Live passenger pickup/drop streams, real-time bus detection confidence scores, student photo enrollment, and edge sync review queue.</div>
                </div>
                <div class="portal-footer">
                    <span>Launch Operations Portal</span>
                    <span class="arrow-icon">→</span>
                </div>
            </a>

            <a href="/management" class="portal-card emerald">
                <div>
                    <div class="portal-header">
                        <span class="portal-emoji">👥</span>
                        <span class="portal-badge badge-green">Fleet Roster</span>
                    </div>
                    <div class="portal-title">Student & Roster Management</div>
                    <div class="portal-desc">Comprehensive student registry: view enrolled faces, update stop assignments, bus routing, CSV report exports, and roster audits.</div>
                </div>
                <div class="portal-footer">
                    <span>Manage Roster Directory</span>
                    <span class="arrow-icon">→</span>
                </div>
            </a>

            <a href="http://localhost:8090" target="_blank" class="portal-card violet">
                <div>
                    <div class="portal-header">
                        <span class="portal-emoji">📸</span>
                        <span class="portal-badge badge-purple">Edge Station :8090</span>
                    </div>
                    <div class="portal-title">Edge Enrollment Kiosk</div>
                    <div class="portal-desc">Rapid on-device camera enrollment station running on the edge device for capturing high-resolution biometric face profiles.</div>
                </div>
                <div class="portal-footer">
                    <span>Open Kiosk (New Window)</span>
                    <span class="arrow-icon">↗</span>
                </div>
            </a>

            <a href="/docs" target="_blank" class="portal-card amber">
                <div>
                    <div class="portal-header">
                        <span class="portal-emoji">⚡</span>
                        <span class="portal-badge badge-amber">OpenAPI v3</span>
                    </div>
                    <div class="portal-title">Swagger API Explorer</div>
                    <div class="portal-desc">Interactive developer documentation covering telemetry ingestion, roster sync, and biometric verification endpoints.</div>
                </div>
                <div class="portal-footer">
                    <span>Explore API Docs</span>
                    <span class="arrow-icon">↗</span>
                </div>
            </a>
        </section>

        <!-- System Architecture Diagnostics -->
        <section class="system-strip">
            <div class="strip-col">
                <span class="strip-label">Backend URL:</span>
                <span class="strip-val" id="sysBackend">http://localhost:8000</span>
            </div>
            <div class="strip-col">
                <span class="strip-label">Biometric Port:</span>
                <span class="strip-val">8095 (Internal)</span>
            </div>
            <div class="strip-col">
                <span class="strip-label">Database:</span>
                <span class="strip-val">SQLite (Local Ready)</span>
            </div>
            <div class="strip-col">
                <span class="strip-label">Last Polled:</span>
                <span class="strip-val" id="lastPolled">Just now</span>
            </div>
        </section>

        <footer>
            SafeBus AI Fleet Architecture &bull; Production Biometric Tracking Engine &bull; Port 8000
        </footer>
    </div>

    <script>
        async function fetchSystemStats() {
            try {
                // Students count
                const sResp = await fetch('/api/students');
                if (sResp.ok) {
                    const sData = await sResp.json();
                    document.getElementById('metricStudents').textContent = sData.total || (sData.students ? sData.students.length : 0);
                }

                // Devices count
                const dResp = await fetch('/api/devices');
                if (dResp.ok) {
                    const dData = await dResp.json();
                    document.getElementById('metricBuses').textContent = dData.length;
                }

                // Events count
                const eResp = await fetch('/api/live?limit=50');
                if (eResp.ok) {
                    const eData = await eResp.json();
                    document.getElementById('metricEvents').textContent = eData.length;
                }

                document.getElementById('lastPolled').textContent = new Date().toLocaleTimeString();
            } catch (err) {
                console.warn('Stats fetch warning:', err);
            }
        }

        fetchSystemStats();
        setInterval(fetchSystemStats, 10000);
    </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def enrollment_dashboard():
    """Unified Fleet Operations Dashboard (Live Events, Enrollment, Students, Devices)."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeBus — Fleet Operations & Biometric Enrollment</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f8fafc;
            --surface: #ffffff;
            --surface-subtle: #f1f5f9;
            --border: #e2e8f0;
            --border-hover: #cbd5e1;
            --text-main: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-dark: #1d4ed8;
            --primary-bg: #eff6ff;
            --emerald: #10b981;
            --emerald-bg: #ecfdf5;
            --amber: #f59e0b;
            --amber-bg: #fffbeb;
            --rose: #ef4444;
            --rose-bg: #fef2f2;
            --sidebar-bg: #090e1a;
            --sidebar-border: #1e293b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
        }

        /* Sidebar Navigation */
        .sidebar {
            width: 260px;
            background: var(--sidebar-bg);
            color: #fff;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            border-right: 1px solid var(--sidebar-border);
            position: sticky;
            top: 0;
            height: 100vh;
            z-index: 50;
        }
        .sidebar-header {
            padding: 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid var(--sidebar-border);
        }
        .sidebar-logo {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, #3b82f6, #6366f1);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }
        .sidebar-title {
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }
        .sidebar-subtitle {
            font-size: 0.72rem;
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .nav-menu {
            padding: 20px 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            flex: 1;
        }
        .nav-label {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #475569;
            padding: 10px 12px 4px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 11px 14px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 10px;
            color: #94a3b8;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s ease;
            text-decoration: none;
        }
        .nav-item-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .nav-item:hover {
            color: #fff;
            background: rgba(255,255,255,0.05);
        }
        .nav-item.active {
            color: #fff;
            background: rgba(59, 130, 246, 0.15);
            border-color: rgba(59, 130, 246, 0.3);
        }
        .nav-badge {
            font-size: 0.72rem;
            padding: 2px 7px;
            border-radius: 999px;
            font-weight: 700;
            background: rgba(255,255,255,0.1);
            color: #cbd5e1;
        }
        .nav-badge.alert {
            background: #ef4444;
            color: #fff;
        }

        .sidebar-footer {
            padding: 18px 20px;
            border-top: 1px solid var(--sidebar-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.78rem;
            color: #64748b;
        }
        .system-dot {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: #10b981;
            font-weight: 600;
        }
        .dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
        }

        /* Main Workspace */
        .workspace {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            max-height: 100vh;
        }

        /* Top Header */
        .topbar {
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 16px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 40;
        }
        .topbar-left h2 {
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }
        .topbar-left p {
            font-size: 0.82rem;
            color: var(--text-secondary);
        }
        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .btn-refresh {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-refresh:hover {
            border-color: var(--border-hover);
            color: var(--text-main);
        }
        .btn-refresh.spinning svg {
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }

        .btn-primary {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 18px;
            background: var(--primary);
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(59, 130, 246, 0.25);
        }
        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
        }

        /* Content Canvas */
        .canvas {
            padding: 32px 36px 64px;
            max-width: 1400px;
        }

        /* Metric Highlight Cards */
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
            margin-bottom: 28px;
        }
        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -8px rgba(0,0,0,0.06);
        }
        .stat-card .val {
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        .stat-card .lbl {
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-top: 4px;
        }
        .stat-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .stat-icon.blue { background: var(--primary-bg); color: var(--primary); }
        .stat-icon.green { background: var(--emerald-bg); color: var(--emerald); }
        .stat-icon.amber { background: var(--amber-bg); color: var(--amber); }
        .stat-icon.rose { background: var(--rose-bg); color: var(--rose); }

        /* Tab Panes */
        .tab-content {
            display: none;
            animation: fadeIn 0.25s ease-out;
        }
        .tab-content.active {
            display: block;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Card Surface */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 24px;
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }
        .card-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
        }
        .card-subtitle {
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Two-Column Enrollment Layout */
        .enroll-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 28px;
        }
        @media (max-width: 1024px) {
            .enroll-grid { grid-template-columns: 1fr; }
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-secondary);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .form-control {
            width: 100%;
            padding: 11px 14px;
            border: 1px solid var(--border);
            border-radius: 10px;
            font-size: 0.92rem;
            font-family: inherit;
            color: var(--text-main);
            background: #fff;
            transition: all 0.2s;
        }
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }

        /* Photo Capture & Upload Studio */
        .photo-studio {
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
        }
        .studio-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }
        .studio-tab-btn {
            flex: 1;
            padding: 9px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #fff;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .studio-tab-btn.active {
            background: var(--primary);
            color: #fff;
            border-color: var(--primary);
        }

        .upload-dropzone {
            border: 2px dashed var(--border-hover);
            border-radius: 12px;
            padding: 36px 20px;
            text-align: center;
            background: #fff;
            cursor: pointer;
            transition: all 0.2s;
        }
        .upload-dropzone:hover, .upload-dropzone.dragover {
            border-color: var(--primary);
            background: var(--primary-bg);
        }
        .upload-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }
        .upload-text {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-main);
        }
        .upload-hint {
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 4px;
        }

        /* Camera Box */
        .camera-box {
            display: none;
            position: relative;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            aspect-ratio: 4/3;
            max-height: 280px;
            margin: 0 auto 16px;
        }
        .camera-box video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .face-guide-oval {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 140px;
            height: 180px;
            border: 2px dashed rgba(255,255,255,0.7);
            border-radius: 50%;
            pointer-events: none;
        }
        .camera-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 12px;
        }

        /* Photo Thumbnails Preview */
        .preview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(75px, 1fr));
            gap: 10px;
            margin-top: 16px;
        }
        .photo-thumb {
            position: relative;
            aspect-ratio: 1;
            border-radius: 10px;
            overflow: hidden;
            border: 2px solid var(--border);
            background: #000;
        }
        .photo-thumb img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .photo-thumb-remove {
            position: absolute;
            top: 4px;
            right: 4px;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: rgba(0,0,0,0.7);
            color: #fff;
            border: none;
            cursor: pointer;
            font-size: 11px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .photo-thumb-remove:hover {
            background: var(--rose);
        }

        /* Tables & Lists */
        .table-responsive {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.88rem;
        }
        th {
            background: var(--surface-subtle);
            padding: 12px 16px;
            text-align: left;
            font-weight: 700;
            color: var(--text-secondary);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }
        td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            color: var(--text-main);
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:hover td {
            background: #fafafa;
        }

        /* Status & Type Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }
        .badge-green { background: var(--emerald-bg); color: #047857; border: 1px solid rgba(16, 185, 129, 0.2); }
        .badge-blue { background: var(--primary-bg); color: var(--primary-dark); border: 1px solid rgba(59, 130, 246, 0.2); }
        .badge-amber { background: var(--amber-bg); color: #b45309; border: 1px solid rgba(245, 158, 11, 0.2); }
        .badge-rose { background: var(--rose-bg); color: #b91c1c; border: 1px solid rgba(239, 68, 68, 0.2); }
        .badge-gray { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }

        /* Filter Controls */
        .filter-bar {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .search-box {
            position: relative;
            flex: 1;
            min-width: 240px;
        }
        .search-box input {
            width: 100%;
            padding: 9px 14px 9px 36px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.88rem;
            font-family: inherit;
        }
        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 14px;
        }

        /* Toast Notifications */
        #toastContainer {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 1000;
        }
        .toast {
            min-width: 280px;
            background: #1e293b;
            color: #fff;
            padding: 14px 18px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            font-size: 0.88rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.25s ease-out;
        }
        .toast.success { background: #065f46; border-left: 4px solid #10b981; }
        .toast.error { background: #881337; border-left: 4px solid #ef4444; }
        .toast.info { background: #1e3a8a; border-left: 4px solid #3b82f6; }
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    </style>
</head>
<body>
    <!-- Sidebar Navigation -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-logo">🚌</div>
            <div>
                <div class="sidebar-title">SafeBus Central</div>
                <div class="sidebar-subtitle">Fleet Operations</div>
            </div>
        </div>

        <nav class="nav-menu">
            <div class="nav-label">Fleet Feeds</div>
            <button class="nav-item active" onclick="switchTab('tabEvents')">
                <div class="nav-item-left"><span>⚡</span><span>Live Event Feed</span></div>
                <span class="nav-badge" id="badgeEventCount">0</span>
            </button>
            <button class="nav-item" onclick="switchTab('tabReview')">
                <div class="nav-item-left"><span>⚠️</span><span>Review Queue</span></div>
                <span class="nav-badge alert" id="badgeReviewCount" style="display: none;">0</span>
            </button>

            <div class="nav-label">Management</div>
            <button class="nav-item" onclick="switchTab('tabEnroll')">
                <div class="nav-item-left"><span>➕</span><span>Enroll Student</span></div>
            </button>
            <button class="nav-item" onclick="switchTab('tabStudents')">
                <div class="nav-item-left"><span>🎓</span><span>Student Roster</span></div>
                <span class="nav-badge" id="badgeStudentCount">0</span>
            </button>
            <button class="nav-item" onclick="switchTab('tabDevices')">
                <div class="nav-item-left"><span>📡</span><span>Bus Edge Devices</span></div>
                <span class="nav-badge" id="badgeDeviceCount">0</span>
            </button>

            <div class="nav-label">External Portals</div>
            <a href="/management" class="nav-item">
                <div class="nav-item-left"><span>👥</span><span>Full Roster Portal</span></div>
                <span>↗</span>
            </a>
            <a href="http://localhost:8090" target="_blank" class="nav-item">
                <div class="nav-item-left"><span>📸</span><span>Edge Kiosk :8090</span></div>
                <span>↗</span>
            </a>
            <a href="/docs" target="_blank" class="nav-item">
                <div class="nav-item-left"><span>📖</span><span>Swagger API</span></div>
                <span>↗</span>
            </a>
        </nav>

        <div class="sidebar-footer">
            <div class="system-dot">
                <span class="dot"></span>
                <span>Port 8000 Online</span>
            </div>
            <a href="/" style="color: #64748b; text-decoration: none; font-size: 11px;">Hub ⤢</a>
        </div>
    </aside>

    <!-- Main Workspace -->
    <main class="workspace">
        <!-- Top Action Bar -->
        <header class="topbar">
            <div class="topbar-left">
                <h2 id="pageTitle">Live Passenger Activity</h2>
                <p id="pageSubtitle">Real-time pickup and drop verifications captured across active bus fleet.</p>
            </div>
            <div class="topbar-actions">
                <button class="btn-refresh" id="refreshBtn" onclick="manualRefresh()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    <span>Refresh</span>
                </button>
                <button class="btn-primary" onclick="switchTab('tabEnroll')">
                    <span>+ Enroll Student</span>
                </button>
            </div>
        </header>

        <div class="canvas">
            <!-- Stat Highlights Bar -->
            <div class="metrics-row">
                <div class="stat-card">
                    <div>
                        <div class="val" id="statStudentTotal">0</div>
                        <div class="lbl">Registered Students</div>
                    </div>
                    <div class="stat-icon blue">🎓</div>
                </div>
                <div class="stat-card">
                    <div>
                        <div class="val" id="statActiveBuses">0</div>
                        <div class="lbl">Buses Online</div>
                    </div>
                    <div class="stat-icon green">🚌</div>
                </div>
                <div class="stat-card">
                    <div>
                        <div class="val" id="statEventsToday">0</div>
                        <div class="lbl">Captured Events</div>
                    </div>
                    <div class="stat-icon amber">⚡</div>
                </div>
                <div class="stat-card">
                    <div>
                        <div class="val" id="statReviewPending">0</div>
                        <div class="lbl">Pending Reviews</div>
                    </div>
                    <div class="stat-icon rose">⚠️</div>
                </div>
            </div>

            <!-- TAB 1: LIVE EVENTS FEED -->
            <div id="tabEvents" class="tab-content active">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Live Passenger Stream</div>
                            <div class="card-subtitle">Showing latest 50 edge verification events</div>
                        </div>
                        <div class="filter-bar" style="margin-bottom: 0;">
                            <select id="eventBusFilter" class="form-control" style="width: auto; padding: 7px 12px; font-size: 0.82rem;" onchange="renderEvents()">
                                <option value="">All Buses</option>
                            </select>
                            <select id="eventTypeFilter" class="form-control" style="width: auto; padding: 7px 12px; font-size: 0.82rem;" onchange="renderEvents()">
                                <option value="">All Event Types</option>
                                <option value="PICKED_UP">Picked Up</option>
                                <option value="DROPPED">Dropped</option>
                                <option value="UNMATCHED_REVIEW">Flagged Review</option>
                            </select>
                        </div>
                    </div>

                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Student</th>
                                    <th>Bus ID</th>
                                    <th>Event Type</th>
                                    <th>Match Confidence</th>
                                    <th>GPS Location</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="eventsTableBody">
                                <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">Connecting to event stream...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 2: REVIEW QUEUE -->
            <div id="tabReview" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Review Queue & Detections</div>
                            <div class="card-subtitle">Unmatched or low-confidence biometric events requiring supervisor sign-off</div>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Event ID</th>
                                    <th>Timestamp</th>
                                    <th>Bus</th>
                                    <th>Confidence</th>
                                    <th>Assign / Match Child ID</th>
                                    <th>Supervisor Action</th>
                                </tr>
                            </thead>
                            <tbody id="reviewTableBody">
                                <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 32px;">No pending review items.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 3: ENROLL STUDENT -->
            <div id="tabEnroll" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Biometric Student Enrollment</div>
                            <div class="card-subtitle">Register a student and generate 128-d face recognition encodings via Face Processor</div>
                        </div>
                    </div>

                    <form id="enrollForm" onsubmit="handleEnrollSubmit(event)">
                        <div class="enroll-grid">
                            <!-- Left: Form Fields -->
                            <div>
                                <div class="form-row">
                                    <div class="form-group">
                                        <label>Child ID *</label>
                                        <input type="text" id="enrollChildId" class="form-control" placeholder="e.g. child_001" required>
                                    </div>
                                    <div class="form-group">
                                        <label>Full Name *</label>
                                        <input type="text" id="enrollName" class="form-control" placeholder="e.g. Arjun Sharma" required>
                                    </div>
                                </div>

                                <div class="form-row">
                                    <div class="form-group">
                                        <label>Assigned Bus *</label>
                                        <input type="text" id="enrollBusId" class="form-control" placeholder="e.g. bus_14" required>
                                    </div>
                                    <div class="form-group">
                                        <label>Twin Group (Optional)</label>
                                        <input type="text" id="enrollTwin" class="form-control" placeholder="e.g. twin_A">
                                    </div>
                                </div>

                                <div class="form-row">
                                    <div class="form-group">
                                        <label>Pickup Stop *</label>
                                        <input type="text" id="enrollPickup" class="form-control" placeholder="e.g. stop_north_gate" required>
                                    </div>
                                    <div class="form-group">
                                        <label>Drop Stop *</label>
                                        <input type="text" id="enrollDrop" class="form-control" placeholder="e.g. stop_main_cross" required>
                                    </div>
                                </div>

                                <div style="margin-top: 24px;">
                                    <button type="submit" id="enrollSubmitBtn" class="btn-primary" style="width: 100%; justify-content: center; padding: 13px;">
                                        <span>Generate Biometric Profile & Enroll</span>
                                    </button>
                                </div>
                            </div>

                            <!-- Right: Photo Capture & Upload Studio -->
                            <div class="photo-studio">
                                <div class="studio-tabs">
                                    <button type="button" class="studio-tab-btn active" id="btnModeUpload" onclick="setStudioMode('upload')">📁 Upload Photos</button>
                                    <button type="button" class="studio-tab-btn" id="btnModeCamera" onclick="setStudioMode('camera')">📸 Live Webcam</button>
                                </div>

                                <!-- Upload Mode -->
                                <div id="studioUploadPane">
                                    <div class="upload-dropzone" id="dropZone" onclick="document.getElementById('fileInput').click()">
                                        <div class="upload-icon">📷</div>
                                        <div class="upload-text">Click or drag & drop photos here</div>
                                        <div class="upload-hint">Upload 3 to 5 clear face photos for robust recognition</div>
                                        <input type="file" id="fileInput" multiple accept="image/*" style="display: none;" onchange="handleFileSelect(event)">
                                    </div>
                                </div>

                                <!-- Webcam Mode -->
                                <div id="studioCameraPane" style="display: none;">
                                    <div class="camera-box">
                                        <video id="webcamVideo" autoplay playsinline muted></video>
                                        <div class="face-guide-oval"></div>
                                    </div>
                                    <div class="camera-actions">
                                        <button type="button" class="btn-primary" onclick="captureWebcamSnapshot()">📸 Snap Photo</button>
                                        <button type="button" class="btn-refresh" onclick="stopWebcam()">Stop Camera</button>
                                    </div>
                                </div>

                                <!-- Selected Photos Preview -->
                                <div style="margin-top: 18px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Selected Photos (<span id="photoCount">0</span>/5)</span>
                                        <button type="button" onclick="clearAllPhotos()" style="background: none; border: none; font-size: 0.75rem; color: var(--rose); cursor: pointer; font-weight: 600;">Clear All</button>
                                    </div>
                                    <div class="preview-grid" id="photoPreviewGrid"></div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>

            <!-- TAB 4: STUDENT ROSTER -->
            <div id="tabStudents" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Enrolled Student Directory</div>
                            <div class="card-subtitle">Active face encodings synchronized across all edge bus devices</div>
                        </div>
                        <a href="/management" class="btn-refresh">Open Advanced Management ↗</a>
                    </div>

                    <div class="filter-bar">
                        <div class="search-box">
                            <span class="search-icon">🔍</span>
                            <input type="text" id="studentSearchInput" placeholder="Search student by name or ID..." oninput="renderStudents()">
                        </div>
                        <select id="studentBusFilter" class="form-control" style="width: auto; font-size: 0.88rem;" onchange="renderStudents()">
                            <option value="">All Buses</option>
                        </select>
                    </div>

                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Child ID</th>
                                    <th>Student Name</th>
                                    <th>Bus Assignment</th>
                                    <th>Pickup Stop</th>
                                    <th>Drop Stop</th>
                                    <th>Encodings</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="studentsTableBody">
                                <tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">Loading student directory...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB 5: BUS EDGE DEVICES -->
            <div id="tabDevices" class="tab-content">
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Registered Fleet Edge Hardware</div>
                            <div class="card-subtitle">Raspberry Pi devices running onboard camera inference and edge synchronization</div>
                        </div>
                    </div>

                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Bus ID</th>
                                    <th>Hardware Status</th>
                                    <th>Last Heartbeat</th>
                                    <th>Connectivity</th>
                                </tr>
                            </thead>
                            <tbody id="devicesTableBody">
                                <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 32px;">Scanning for active edge devices...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Notification Toast Container -->
    <div id="toastContainer"></div>

    <script>
        // State Store
        let state = {
            events: [],
            students: [],
            devices: [],
            reviews: [],
            photos: []
        };

        let webcamStream = null;

        // Tab Navigation
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            const targetTab = document.getElementById(tabId);
            if (targetTab) targetTab.classList.add('active');

            // Find matching button
            const buttons = document.querySelectorAll('.nav-item');
            buttons.forEach(btn => {
                if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
                    btn.classList.add('active');
                }
            });

            // Update Page Header Title
            const titles = {
                tabEvents: { t: "Live Passenger Activity", s: "Real-time pickup and drop verifications captured across active bus fleet." },
                tabReview: { t: "Review Queue & Flagged Detections", s: "Supervisor review for low-confidence or unmatched student boardings." },
                tabEnroll: { t: "Student Biometric Enrollment", s: "Register new students with face photos and generate recognition encodings." },
                tabStudents: { t: "Enrolled Student Roster", s: "Browse, filter, and audit biometric face encodings across all buses." },
                tabDevices: { t: "Fleet Edge Hardware Status", s: "Real-time telemetry and heartbeat monitoring from Raspberry Pi bus cameras." }
            };
            if (titles[tabId]) {
                document.getElementById('pageTitle').textContent = titles[tabId].t;
                document.getElementById('pageSubtitle').textContent = titles[tabId].s;
            }

            if (tabId !== 'tabEnroll' && webcamStream) {
                stopWebcam();
            }
        }

        // Notification Toast
        function showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            const icon = type === 'success' ? '✓' : (type === 'error' ? '✗' : 'ℹ');
            toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(10px)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        // Fetch Core Data
        async function fetchAllData() {
            const refreshBtn = document.getElementById('refreshBtn');
            refreshBtn.classList.add('spinning');

            try {
                // Events
                const evResp = await fetch('/api/live?limit=50');
                if (evResp.ok) state.events = await evResp.json();

                // Students
                const stResp = await fetch('/api/students');
                if (stResp.ok) {
                    const stData = await stResp.json();
                    state.students = stData.students || stData || [];
                }

                // Devices
                const devResp = await fetch('/api/devices');
                if (devResp.ok) state.devices = await devResp.json();

                // Reviews
                const revResp = await fetch('/api/review');
                if (revResp.ok) state.reviews = await revResp.json();

                updateUI();
            } catch (err) {
                console.error("Data refresh error:", err);
            } finally {
                refreshBtn.classList.remove('spinning');
            }
        }

        function manualRefresh() {
            fetchAllData().then(() => showToast("Telemetry feed refreshed", "info"));
        }

        function updateUI() {
            // Update Metric Counts
            document.getElementById('statStudentTotal').textContent = state.students.length;
            document.getElementById('badgeStudentCount').textContent = state.students.length;

            const onlineBuses = state.devices.filter(d => d.status === 'online').length;
            document.getElementById('statActiveBuses').textContent = onlineBuses || state.devices.length;
            document.getElementById('badgeDeviceCount').textContent = state.devices.length;

            document.getElementById('statEventsToday').textContent = state.events.length;
            document.getElementById('badgeEventCount').textContent = state.events.length;

            document.getElementById('statReviewPending').textContent = state.reviews.length;
            const revBadge = document.getElementById('badgeReviewCount');
            if (state.reviews.length > 0) {
                revBadge.style.display = 'inline-block';
                revBadge.textContent = state.reviews.length;
            } else {
                revBadge.style.display = 'none';
            }

            // Populate Bus Filters
            const buses = Array.from(new Set(state.students.map(s => s.assigned_bus_id).filter(Boolean)));
            const busSelects = [document.getElementById('eventBusFilter'), document.getElementById('studentBusFilter')];
            busSelects.forEach(select => {
                if (!select) return;
                const currentVal = select.value;
                select.innerHTML = '<option value="">All Buses</option>';
                buses.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b;
                    opt.textContent = b;
                    select.appendChild(opt);
                });
                select.value = currentVal;
            });

            renderEvents();
            renderStudents();
            renderDevices();
            renderReviews();
        }

        // Render Events Feed
        function renderEvents() {
            const tbody = document.getElementById('eventsTableBody');
            const busFilter = document.getElementById('eventBusFilter').value;
            const typeFilter = document.getElementById('eventTypeFilter').value;

            let filtered = state.events;
            if (busFilter) filtered = filtered.filter(e => e.bus_id === busFilter);
            if (typeFilter) filtered = filtered.filter(e => e.event_type === typeFilter);

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">No matching passenger events found.</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(e => {
                let badgeClass = 'badge-gray';
                let icon = '•';
                if (e.event_type === 'PICKED_UP') { badgeClass = 'badge-green'; icon = '↑'; }
                else if (e.event_type === 'DROPPED') { badgeClass = 'badge-blue'; icon = '↓'; }
                else if (e.event_type === 'UNMATCHED_REVIEW') { badgeClass = 'badge-amber'; icon = '⚠'; }

                const conf = e.confidence ? (e.confidence * 100).toFixed(1) + '%' : 'N/A';
                const timeStr = new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                const studentName = getStudentName(e.child_id);

                return `
                    <tr>
                        <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-secondary);">${timeStr}</td>
                        <td><strong>${studentName}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">(${e.child_id || 'Unknown'})</span></td>
                        <td><span class="badge badge-gray">${e.bus_id || 'Fleet'}</span></td>
                        <td><span class="badge ${badgeClass}">${icon} ${e.event_type}</span></td>
                        <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;">${conf}</td>
                        <td style="font-size: 0.8rem; color: var(--text-secondary);">${e.gps_lat ? `${e.gps_lat.toFixed(4)}, ${e.gps_lng.toFixed(4)}` : '<span style="color: #cbd5e1;">No GPS</span>'}</td>
                        <td><span style="font-size: 0.78rem; color: var(--text-secondary);">${e.review_status || 'verified'}</span></td>
                    </tr>
                `;
            }).join('');
        }

        function getStudentName(childId) {
            if (!childId) return 'Unidentified';
            const s = state.students.find(st => st.child_id === childId);
            return s ? s.name : childId;
        }

        // Render Student Roster
        function renderStudents() {
            const tbody = document.getElementById('studentsTableBody');
            const search = (document.getElementById('studentSearchInput').value || '').toLowerCase();
            const busFilter = document.getElementById('studentBusFilter').value;

            let filtered = state.students;
            if (busFilter) filtered = filtered.filter(s => s.assigned_bus_id === busFilter);
            if (search) {
                filtered = filtered.filter(s => 
                    (s.name && s.name.toLowerCase().includes(search)) ||
                    (s.child_id && s.child_id.toLowerCase().includes(search))
                );
            }

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px;">No enrolled students found.</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(s => `
                <tr>
                    <td><code style="background: var(--surface-subtle); padding: 3px 6px; border-radius: 4px; font-size: 0.8rem;">${s.child_id}</code></td>
                    <td><strong>${s.name}</strong></td>
                    <td><span class="badge badge-blue">${s.assigned_bus_id || 'Unassigned'}</span></td>
                    <td>${s.pickup_stop_id || '-'}</td>
                    <td>${s.drop_stop_id || '-'}</td>
                    <td><span class="badge badge-green">${s.encoding_count || 1} Encodings</span></td>
                    <td>
                        <button onclick="quickDeleteStudent('${s.child_id}', '${s.name}')" style="background: none; border: none; color: var(--rose); cursor: pointer; font-weight: 600; font-size: 0.82rem;">Delete</button>
                    </td>
                </tr>
            `).join('');
        }

        // Render Edge Devices
        function renderDevices() {
            const tbody = document.getElementById('devicesTableBody');
            if (!state.devices || state.devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 32px;">No bus edge devices registered yet.</td></tr>';
                return;
            }

            tbody.innerHTML = state.devices.map(d => {
                const isOnline = d.status === 'online';
                const statusBadge = isOnline 
                    ? '<span class="badge badge-green"><span class="dot"></span> Online</span>'
                    : '<span class="badge badge-rose">Offline</span>';

                return `
                    <tr>
                        <td><strong>${d.bus_id}</strong></td>
                        <td>${statusBadge}</td>
                        <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;">${d.last_heartbeat ? new Date(d.last_heartbeat).toLocaleTimeString() : 'Never'}</td>
                        <td><span style="font-size: 0.82rem; color: var(--text-secondary);">${isOnline ? 'Edge Sync Active' : 'Disconnected'}</span></td>
                    </tr>
                `;
            }).join('');
        }

        // Render Review Queue
        function renderReviews() {
            const tbody = document.getElementById('reviewTableBody');
            if (!state.reviews || state.reviews.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 32px;">✓ All detections reviewed. Review queue is clear.</td></tr>';
                return;
            }

            tbody.innerHTML = state.reviews.map(r => `
                <tr>
                    <td><code>#${r.id}</code></td>
                    <td>${new Date(r.timestamp).toLocaleTimeString()}</td>
                    <td><span class="badge badge-gray">${r.bus_id}</span></td>
                    <td>${r.confidence ? (r.confidence * 100).toFixed(1) + '%' : 'Low'}</td>
                    <td>
                        <input type="text" id="reviewChild_${r.id}" placeholder="Enter Child ID" class="form-control" style="padding: 4px 8px; font-size: 0.82rem; width: 140px;">
                    </td>
                    <td>
                        <button onclick="resolveReviewItem(${r.id}, 'confirmed')" class="btn-primary" style="padding: 5px 10px; font-size: 0.78rem;">Confirm</button>
                        <button onclick="resolveReviewItem(${r.id}, 'rejected')" class="btn-refresh" style="padding: 5px 10px; font-size: 0.78rem; color: var(--rose);">Reject</button>
                    </td>
                </tr>
            `).join('');
        }

        async function resolveReviewItem(eventId, decision) {
            const childInput = document.getElementById(`reviewChild_${eventId}`);
            const childId = childInput ? childInput.value.trim() : null;

            try {
                const url = `/api/review/${eventId}/resolve?decision=${decision}${childId ? `&confirmed_child_id=${encodeURIComponent(childId)}` : ''}`;
                const resp = await fetch(url, { method: 'POST' });
                if (resp.ok) {
                    showToast(`Event #${eventId} marked as ${decision}`, 'success');
                    fetchAllData();
                } else {
                    showToast('Failed to resolve review item', 'error');
                }
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        async function quickDeleteStudent(childId, name) {
            if (!confirm(`Delete student record for "${name}" (${childId})?`)) return;
            try {
                const resp = await fetch(`/api/students/${childId}`, { method: 'DELETE' });
                if (resp.ok) {
                    showToast(`Deleted ${name}`, 'success');
                    fetchAllData();
                } else {
                    showToast('Could not delete student', 'error');
                }
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        // Photo Studio Functionality
        function setStudioMode(mode) {
            document.getElementById('btnModeUpload').classList.toggle('active', mode === 'upload');
            document.getElementById('btnModeCamera').classList.toggle('active', mode === 'camera');
            document.getElementById('studioUploadPane').style.display = mode === 'upload' ? 'block' : 'none';
            document.getElementById('studioCameraPane').style.display = mode === 'camera' ? 'block' : 'none';

            if (mode === 'camera') {
                startWebcam();
            } else {
                stopWebcam();
            }
        }

        async function startWebcam() {
            try {
                webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
                const videoEl = document.getElementById('webcamVideo');
                videoEl.srcObject = webcamStream;
                document.querySelector('.camera-box').style.display = 'block';
            } catch (err) {
                showToast("Could not access camera: " + err.message, "error");
                setStudioMode('upload');
            }
        }

        function stopWebcam() {
            if (webcamStream) {
                webcamStream.getTracks().forEach(t => t.stop());
                webcamStream = null;
            }
            const box = document.querySelector('.camera-box');
            if (box) box.style.display = 'none';
        }

        function captureWebcamSnapshot() {
            if (state.photos.length >= 5) {
                showToast("Maximum 5 photos reached", "info");
                return;
            }

            const video = document.getElementById('webcamVideo');
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const b64 = canvas.toDataURL('image/jpeg', 0.9).split(',')[1];
            state.photos.push(b64);
            renderPhotoGrid();
            showToast(`Photo #${state.photos.length} captured`, "success");
        }

        function handleFileSelect(evt) {
            const files = Array.from(evt.target.files);
            if (files.length === 0) return;

            files.forEach(file => {
                if (state.photos.length >= 5) return;
                const reader = new FileReader();
                reader.onload = (e) => {
                    const b64 = e.target.result.split(',')[1];
                    state.photos.push(b64);
                    renderPhotoGrid();
                };
                reader.readAsDataURL(file);
            });
            evt.target.value = '';
        }

        function renderPhotoGrid() {
            const grid = document.getElementById('photoPreviewGrid');
            document.getElementById('photoCount').textContent = state.photos.length;

            grid.innerHTML = state.photos.map((b64, idx) => `
                <div class="photo-thumb">
                    <img src="data:image/jpeg;base64,${b64}">
                    <button type="button" class="photo-thumb-remove" onclick="removePhoto(${idx})">✕</button>
                </div>
            `).join('');
        }

        function removePhoto(idx) {
            state.photos.splice(idx, 1);
            renderPhotoGrid();
        }

        function clearAllPhotos() {
            state.photos = [];
            renderPhotoGrid();
        }

        // Enrollment Submission
        async function handleEnrollSubmit(evt) {
            evt.preventDefault();
            if (state.photos.length === 0) {
                showToast("Please provide at least 1 photo for face recognition", "error");
                return;
            }

            const submitBtn = document.getElementById('enrollSubmitBtn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span>Processing Face Encodings...</span>';

            const payload = {
                child_id: document.getElementById('enrollChildId').value.trim(),
                name: document.getElementById('enrollName').value.trim(),
                bus_id: document.getElementById('enrollBusId').value.trim(),
                pickup_stop_id: document.getElementById('enrollPickup').value.trim(),
                drop_stop_id: document.getElementById('enrollDrop').value.trim(),
                twin_group: document.getElementById('enrollTwin').value.trim() || null,
                photos: state.photos
            };

            try {
                const resp = await fetch('/api/enroll/centralized', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await resp.json();

                if (resp.ok && result.status === 'success') {
                    showToast(`✓ Enrolled ${payload.name} with ${result.encodings_count || 1} face encodings!`, "success");
                    document.getElementById('enrollForm').reset();
                    clearAllPhotos();
                    fetchAllData();
                    switchTab('tabStudents');
                } else {
                    showToast(result.message || 'Enrollment failed. Face processor could not detect a face.', "error");
                }
            } catch (err) {
                showToast("Network error during enrollment: " + err.message, "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>Generate Biometric Profile & Enroll</span>';
            }
        }

        // Auto polling every 5 seconds for real-time monitoring
        fetchAllData();
        setInterval(fetchAllData, 5000);
    </script>
</body>
</html>
"""


@router.get("/management", response_class=HTMLResponse)
def management_dashboard():
    """Student Roster & Fleet Operations Management Portal."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeBus — Fleet Student Registry & Operations</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f8fafc;
            --surface: #ffffff;
            --surface-subtle: #f1f5f9;
            --border: #e2e8f0;
            --border-hover: #cbd5e1;
            --text-main: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --primary: #4f46e5;
            --primary-dark: #4338ca;
            --primary-bg: #eef2ff;
            --emerald: #10b981;
            --emerald-bg: #ecfdf5;
            --rose: #ef4444;
            --rose-bg: #fef2f2;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
        }

        .header-bar {
            background: #0b0f19;
            color: #fff;
            padding: 20px 48px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #1e293b;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .header-logo {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: linear-gradient(135deg, #4f46e5, #06b6d4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .header-title h1 {
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }
        .header-title p {
            font-size: 0.78rem;
            color: #94a3b8;
        }
        .header-links {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .header-link {
            color: #cbd5e1;
            text-decoration: none;
            font-size: 0.88rem;
            font-weight: 600;
            padding: 8px 14px;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .header-link:hover {
            color: #fff;
            background: rgba(255,255,255,0.08);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 48px 80px;
        }

        /* Metric Cards */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 22px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .metric-card .val {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.03em;
        }
        .metric-card .lbl {
            font-size: 0.82rem;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .metric-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: var(--surface-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }

        /* Actions Bar */
        .controls-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }
        .controls-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }
        .search-group {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
            min-width: 280px;
        }
        .input-search {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.92rem;
            font-family: inherit;
        }
        .select-filter {
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.92rem;
            font-family: inherit;
            background: #fff;
        }
        .btn-action-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
            text-decoration: none;
        }
        .btn-primary {
            background: var(--primary);
            color: #fff;
        }
        .btn-primary:hover {
            background: var(--primary-dark);
        }
        .btn-outline {
            background: #fff;
            border-color: var(--border);
            color: var(--text-secondary);
        }
        .btn-outline:hover {
            border-color: var(--border-hover);
            color: var(--text-main);
        }
        .btn-danger {
            background: var(--rose-bg);
            border-color: rgba(239, 68, 68, 0.3);
            color: #b91c1c;
        }
        .btn-danger:hover {
            background: var(--rose);
            color: #fff;
        }

        /* Registry Table */
        .table-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        th {
            background: var(--surface-subtle);
            padding: 14px 20px;
            text-align: left;
            font-weight: 700;
            color: var(--text-secondary);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }
        td {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #fafbfc; }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .badge-indigo { background: var(--primary-bg); color: var(--primary); border: 1px solid rgba(79, 70, 229, 0.2); }
        .badge-green { background: var(--emerald-bg); color: var(--emerald); border: 1px solid rgba(16, 185, 129, 0.2); }
        .badge-gray { background: #f1f5f9; color: #475569; }

        /* Modal Dialog */
        .modal-backdrop {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(4px);
            z-index: 200;
            align-items: center;
            justify-content: center;
        }
        .modal-backdrop.open { display: flex; }
        .modal {
            background: #fff;
            border-radius: 16px;
            width: 100%;
            max-width: 520px;
            padding: 32px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            animation: modalIn 0.2s ease-out;
        }
        @keyframes modalIn {
            from { transform: scale(0.96); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
        }
        .modal-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--text-main);
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 20px;
            color: var(--text-muted);
            cursor: pointer;
        }
        .modal-body .form-group {
            margin-bottom: 16px;
        }
        .modal-body label {
            display: block;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }
        .modal-footer {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 12px;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }

        /* Toast */
        #toastContainer {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 1000;
        }
        .toast {
            background: #1e293b;
            color: #fff;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 0.88rem;
            font-weight: 600;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            margin-top: 10px;
        }
        .toast.success { background: #065f46; border-left: 4px solid #10b981; }
        .toast.error { background: #881337; border-left: 4px solid #ef4444; }
    </style>
</head>
<body>
    <header class="header-bar">
        <div class="header-left">
            <div class="header-logo">👥</div>
            <div class="header-title">
                <h1>SafeBus Student Roster & Fleet Registry</h1>
                <p>Centralized identity management & edge encoding distribution</p>
            </div>
        </div>
        <div class="header-links">
            <a href="/dashboard" class="header-link">📊 Fleet Operations</a>
            <a href="/" class="header-link">Command Hub</a>
        </div>
    </header>

    <div class="container">
        <!-- Stat Cards -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div>
                    <div class="val" id="metricTotalStudents">0</div>
                    <div class="lbl">Total Enrolled</div>
                </div>
                <div class="metric-icon">🎓</div>
            </div>
            <div class="metric-card">
                <div>
                    <div class="val" id="metricTotalEncodings">0</div>
                    <div class="lbl">Face Encodings</div>
                </div>
                <div class="metric-icon">⚡</div>
            </div>
            <div class="metric-card">
                <div>
                    <div class="val" id="metricBuses">0</div>
                    <div class="lbl">Fleet Routes</div>
                </div>
                <div class="metric-icon">🚌</div>
            </div>
            <div class="metric-card">
                <div>
                    <div class="val" id="metricTwinGroups">0</div>
                    <div class="lbl">Twin Clusters</div>
                </div>
                <div class="metric-icon">👥</div>
            </div>
        </div>

        <!-- Controls Bar -->
        <div class="controls-card">
            <div class="controls-row">
                <div class="search-group">
                    <input type="text" id="searchInput" class="input-search" placeholder="Search by name, child ID, or stop..." oninput="filterStudents()">
                    <select id="busFilterSelect" class="select-filter" onchange="filterStudents()">
                        <option value="">All Fleet Buses</option>
                    </select>
                </div>
                <div class="btn-action-group">
                    <button onclick="loadStudents()" class="btn btn-outline">🔄 Refresh</button>
                    <a href="/api/students/export/csv" class="btn btn-outline">📥 Export CSV</a>
                    <a href="/dashboard" class="btn btn-primary">+ Enroll Student</a>
                    <button onclick="openDeleteAllModal()" class="btn btn-danger">🗑️ Bulk Reset</button>
                </div>
            </div>
        </div>

        <!-- Students Table -->
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>Child ID</th>
                        <th>Student Name</th>
                        <th>Bus Assignment</th>
                        <th>Pickup Stop</th>
                        <th>Drop Stop</th>
                        <th>Twin Group</th>
                        <th>Encodings</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody id="studentTableBody">
                    <tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 48px;">Loading roster registry...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Edit Student Modal -->
    <div id="editModal" class="modal-backdrop">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title">Edit Student Details</div>
                <button class="modal-close" onclick="closeEditModal()">✕</button>
            </div>
            <form id="editForm" onsubmit="saveStudentEdit(event)">
                <div class="modal-body">
                    <input type="hidden" id="editChildId">
                    <div class="form-group">
                        <label>Student Name</label>
                        <input type="text" id="editName" class="input-search" required style="width: 100%;">
                    </div>
                    <div class="form-group">
                        <label>Assigned Bus</label>
                        <input type="text" id="editBus" class="input-search" required style="width: 100%;">
                    </div>
                    <div class="form-group">
                        <label>Pickup Stop ID</label>
                        <input type="text" id="editPickup" class="input-search" required style="width: 100%;">
                    </div>
                    <div class="form-group">
                        <label>Drop Stop ID</label>
                        <input type="text" id="editDrop" class="input-search" required style="width: 100%;">
                    </div>
                    <div class="form-group">
                        <label>Twin Group</label>
                        <input type="text" id="editTwin" class="input-search" style="width: 100%;" placeholder="None">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline" onclick="closeEditModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Delete All Modal -->
    <div id="deleteAllModal" class="modal-backdrop">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title" style="color: var(--rose);">⚠️ Danger: Reset Entire Roster</div>
                <button class="modal-close" onclick="closeDeleteAllModal()">✕</button>
            </div>
            <div class="modal-body">
                <p style="font-size: 0.92rem; color: var(--text-secondary); margin-bottom: 16px;">This will permanently wipe <strong>all registered students and their facial encodings</strong>. Edge devices will be forced to re-sync empty rosters.</p>
                <p style="font-size: 0.85rem; font-weight: 700; margin-bottom: 8px;">Type <code style="background: #f1f5f9; padding: 2px 6px;">DELETE-ALL</code> to confirm:</p>
                <input type="text" id="confirmDeleteInput" class="input-search" style="width: 100%; border-color: var(--rose);" placeholder="DELETE-ALL">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeDeleteAllModal()">Cancel</button>
                <button type="button" class="btn btn-danger" onclick="executeDeleteAll()">Confirm Permanent Wipe</button>
            </div>
        </div>
    </div>

    <div id="toastContainer"></div>

    <script>
        let allStudents = [];

        function showToast(msg, type = 'success') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = msg;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3500);
        }

        async function loadStudents() {
            try {
                const resp = await fetch('/api/students');
                const data = await resp.json();
                allStudents = data.students || data || [];
                updateMetrics();
                populateBusFilter();
                filterStudents();
            } catch (err) {
                document.getElementById('studentTableBody').innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 48px;">Error loading students: ${err.message}</td></tr>`;
            }
        }

        function updateMetrics() {
            document.getElementById('metricTotalStudents').textContent = allStudents.length;
            const totalEncodings = allStudents.reduce((acc, s) => acc + (s.encoding_count || 1), 0);
            document.getElementById('metricTotalEncodings').textContent = totalEncodings;
            const buses = new Set(allStudents.map(s => s.assigned_bus_id).filter(Boolean));
            document.getElementById('metricBuses').textContent = buses.size;
            const twins = new Set(allStudents.map(s => s.twin_group).filter(Boolean));
            document.getElementById('metricTwinGroups').textContent = twins.size;
        }

        function populateBusFilter() {
            const select = document.getElementById('busFilterSelect');
            const current = select.value;
            const buses = Array.from(new Set(allStudents.map(s => s.assigned_bus_id).filter(Boolean)));
            select.innerHTML = '<option value="">All Fleet Buses</option>';
            buses.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b;
                opt.textContent = b;
                select.appendChild(opt);
            });
            select.value = current;
        }

        function filterStudents() {
            const search = (document.getElementById('searchInput').value || '').toLowerCase();
            const bus = document.getElementById('busFilterSelect').value;

            let filtered = allStudents;
            if (bus) filtered = filtered.filter(s => s.assigned_bus_id === bus);
            if (search) {
                filtered = filtered.filter(s => 
                    (s.name && s.name.toLowerCase().includes(search)) ||
                    (s.child_id && s.child_id.toLowerCase().includes(search)) ||
                    (s.pickup_stop_id && s.pickup_stop_id.toLowerCase().includes(search)) ||
                    (s.drop_stop_id && s.drop_stop_id.toLowerCase().includes(search))
                );
            }

            renderTable(filtered);
        }

        function renderTable(students) {
            const tbody = document.getElementById('studentTableBody');
            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 48px;">No students matching the criteria.</td></tr>';
                return;
            }

            tbody.innerHTML = students.map(s => `
                <tr>
                    <td><code style="background: var(--surface-subtle); padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;">${s.child_id}</code></td>
                    <td><strong>${s.name}</strong></td>
                    <td><span class="badge badge-indigo">${s.assigned_bus_id || 'Unassigned'}</span></td>
                    <td>${s.pickup_stop_id || '-'}</td>
                    <td>${s.drop_stop_id || '-'}</td>
                    <td>${s.twin_group ? `<span class="badge badge-gray">${s.twin_group}</span>` : '-'}</td>
                    <td><span class="badge badge-green">${s.encoding_count || 1} Encodings</span></td>
                    <td style="text-align: right;">
                        <button onclick="openEditModal('${s.child_id}')" class="btn btn-outline" style="padding: 5px 10px; font-size: 0.78rem;">Edit</button>
                        <button onclick="deleteSingleStudent('${s.child_id}', '${s.name}')" class="btn btn-danger" style="padding: 5px 10px; font-size: 0.78rem;">Delete</button>
                    </td>
                </tr>
            `).join('');
        }

        function openEditModal(childId) {
            const s = allStudents.find(st => st.child_id === childId);
            if (!s) return;
            document.getElementById('editChildId').value = s.child_id;
            document.getElementById('editName').value = s.name;
            document.getElementById('editBus').value = s.assigned_bus_id || '';
            document.getElementById('editPickup').value = s.pickup_stop_id || '';
            document.getElementById('editDrop').value = s.drop_stop_id || '';
            document.getElementById('editTwin').value = s.twin_group || '';
            document.getElementById('editModal').classList.add('open');
        }

        function closeEditModal() {
            document.getElementById('editModal').classList.remove('open');
        }

        async function saveStudentEdit(evt) {
            evt.preventDefault();
            const childId = document.getElementById('editChildId').value;
            const payload = {
                name: document.getElementById('editName').value.trim(),
                assigned_bus_id: document.getElementById('editBus').value.trim(),
                pickup_stop_id: document.getElementById('editPickup').value.trim(),
                drop_stop_id: document.getElementById('editDrop').value.trim(),
                twin_group: document.getElementById('editTwin').value.trim() || null
            };

            try {
                const resp = await fetch(`/api/students/${childId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (resp.ok) {
                    showToast(`Updated ${payload.name}`, 'success');
                    closeEditModal();
                    loadStudents();
                } else {
                    showToast('Failed to update student', 'error');
                }
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        async function deleteSingleStudent(childId, name) {
            if (!confirm(`Permanently remove student "${name}" (${childId}) from fleet roster?`)) return;
            try {
                const resp = await fetch(`/api/students/${childId}`, { method: 'DELETE' });
                if (resp.ok) {
                    showToast(`Deleted ${name}`, 'success');
                    loadStudents();
                } else {
                    showToast('Could not delete student', 'error');
                }
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        function openDeleteAllModal() {
            document.getElementById('confirmDeleteInput').value = '';
            document.getElementById('deleteAllModal').classList.add('open');
        }

        function closeDeleteAllModal() {
            document.getElementById('deleteAllModal').classList.remove('open');
        }

        async function executeDeleteAll() {
            const val = document.getElementById('confirmDeleteInput').value.trim();
            if (val !== 'DELETE-ALL') {
                showToast('Please type DELETE-ALL exactly to confirm', 'error');
                return;
            }

            try {
                const resp = await fetch('/api/students?confirm=yes-delete-all', { method: 'DELETE' });
                if (resp.ok) {
                    showToast('Entire student roster has been reset', 'success');
                    closeDeleteAllModal();
                    loadStudents();
                } else {
                    showToast('Failed to delete all students', 'error');
                }
            } catch (err) {
                showToast(err.message, 'error');
            }
        }

        loadStudents();
    </script>
</body>
</html>
"""
