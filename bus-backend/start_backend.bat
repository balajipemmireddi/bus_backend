@echo off
REM Run this to start the backend. Double-click it, or run from PowerShell/cmd.
REM Edit PI_IP below to match your Pi's actual IP address.

set PI_IP=192.168.1.72
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

python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
