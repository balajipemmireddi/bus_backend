@echo off
REM Run this to start the backend. Double-click it, or run from PowerShell/cmd.
REM Edit PI_IP below to match your Pi's actual IP address.

set PI_IP=192.168.1.85
set FACE_PROCESSOR_URL=http://%PI_IP%:8095

echo ============================================
echo   Bus Backend - starting
echo   Face processor target: %FACE_PROCESSOR_URL%
echo   Dashboard will be at:  http://localhost:8000/dashboard
echo ============================================
echo.
echo IMPORTANT: face_processor.py must already be running on the Pi
echo (see start_edge.sh) or enrollment will fail with "face processor unreachable".
echo.
echo Network verification:
echo   Windows backend:     192.168.1.72:8000 (this machine)
echo   Pi face processor:   192.168.1.85:8095 (REQUIRED)
echo.
echo If you get "connection refused" errors, verify:
echo   1. Pi is running: bash start_edge.sh
echo   2. Pi is on network and IP is 192.168.1.85
echo   3. Windows can reach Pi: Test-NetConnection 192.168.1.85 -Port 8095
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
