# Network Configuration Diagnostic Script for Windows
# Run on Windows: powershell -ExecutionPolicy Bypass -File test_network_config.ps1

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Bus Backend - Network Configuration Test" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Get .env configuration
$env_file = ".env"
if (Test-Path $env_file) {
    Write-Host "✓ Found .env file" -ForegroundColor Green
} else {
    Write-Host "! .env not found, using defaults" -ForegroundColor Yellow
    $env_file = ".env.example"
}

# Parse .env file
$config = @{}
Get-Content $env_file | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        $config[$key] = $value
    }
}

Write-Host ""
Write-Host "Current Configuration:" -ForegroundColor Cyan
Write-Host "  BACKEND_HOST: $($config['BACKEND_HOST'])"
Write-Host "  BACKEND_PORT: $($config['BACKEND_PORT'])"
Write-Host "  FACE_PROCESSOR_URL: $($config['FACE_PROCESSOR_URL'])"
Write-Host "  DATABASE_URL: $($config['DATABASE_URL'])"
Write-Host ""

# Get Windows IP
Write-Host "This Windows PC IP addresses:" -ForegroundColor Cyan
$ipv4_addresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } | Select-Object -ExpandProperty IPAddress
$ipv4_addresses | ForEach-Object {
    Write-Host "  $_"
}
$this_windows_ip = $ipv4_addresses[0]
Write-Host "  Primary IP: $this_windows_ip" -ForegroundColor Green
Write-Host ""

# Extract Pi IP from FACE_PROCESSOR_URL
$pi_ip = $config['FACE_PROCESSOR_URL'] -replace 'http://(\d+\.\d+\.\d+\.\d+):.*/.*', '$1'
Write-Host "FACE_PROCESSOR_URL points to Pi at: $pi_ip" -ForegroundColor Cyan
Write-Host ""

# Verify Pi IP is different from Windows IP
if ($pi_ip -eq $this_windows_ip) {
    Write-Host "✗ ERROR: FACE_PROCESSOR_URL is pointing to THIS Windows PC ($pi_ip)" -ForegroundColor Red
    Write-Host "  It should point to the Raspberry Pi instead!" -ForegroundColor Red
    Write-Host "  Find Pi IP, then update .env:" -ForegroundColor Yellow
    Write-Host "  FACE_PROCESSOR_URL=http://<PI_IP>:8095" -ForegroundColor Yellow
    Write-Host ""
    exit 1
} else {
    Write-Host "✓ FACE_PROCESSOR_URL correctly points to Pi at $pi_ip" -ForegroundColor Green
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Testing Connectivity" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Test backend (local)
Write-Host "Testing Backend (localhost:8000)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Backend health check passed" -ForegroundColor Green
    Write-Host "  Response: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "✗ Cannot reach backend at http://localhost:8000" -ForegroundColor Red
    Write-Host "  Is backend running? (python -m uvicorn main:app --host 0.0.0.0 --port 8000)" -ForegroundColor Yellow
}

Write-Host ""

# Test Pi connectivity
Write-Host "Testing Pi connectivity ($pi_ip)..." -ForegroundColor Cyan
try {
    $connection = Test-NetConnection -ComputerName $pi_ip -Port 8095 -WarningAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        Write-Host "✓ Can reach Pi at $($pi_ip):8095" -ForegroundColor Green
        
        # Try to reach face_processor
        try {
            $fp_response = Invoke-WebRequest -Uri "http://$($pi_ip):8095/health" -UseBasicParsing -TimeoutSec 5
            Write-Host "✓ Face processor is running on Pi" -ForegroundColor Green
            Write-Host "  Response: $($fp_response.Content)" -ForegroundColor Green
        } catch {
            Write-Host "⚠ Can reach Pi but face_processor not responding" -ForegroundColor Yellow
            Write-Host "  Is face_processor running? (run 'bash start_edge.sh' on Pi)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Cannot reach Pi at $($pi_ip):8095" -ForegroundColor Red
        Write-Host "  Check:" -ForegroundColor Yellow
        Write-Host "    - Is Pi IP correct? (should be 192.168.1.85)" -ForegroundColor Yellow
        Write-Host "    - Is Pi on the network?" -ForegroundColor Yellow
        Write-Host "    - Is firewall blocking port 8095?" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Error testing connection: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Network topology:" -ForegroundColor Cyan
Write-Host "  This Windows PC: $this_windows_ip (backend on :8000)" -ForegroundColor Green
Write-Host "  Raspberry Pi: $pi_ip (face_processor on :8095)" -ForegroundColor Green
Write-Host ""
Write-Host "If you see ✓ for all tests above, everything is configured correctly!" -ForegroundColor Green
Write-Host ""
