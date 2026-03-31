@echo off
setlocal

cd /d "%~dp0"

set "LOCAL_IP="
if not "%~1"=="" (
	set "LOCAL_IP=%~1"
) else (
	for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$ip = (Get-NetIPConfiguration ^| Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.IPv4Address -ne $null } ^| Select-Object -First 1).IPv4Address.IPAddress; if ($ip) { Write-Output $ip }"`) do set "LOCAL_IP=%%i"
)

echo(%LOCAL_IP%| findstr /R "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 set "LOCAL_IP="

if "%LOCAL_IP%"=="" (
	echo [WARN] Failed to auto-detect a valid LAN IPv4.
	set /p LOCAL_IP=Please input your LAN IPv4 manually, press Enter for 127.0.0.1: 
)

if "%LOCAL_IP%"=="" set "LOCAL_IP=127.0.0.1"

echo [LAN] Local IP detected: %LOCAL_IP%
echo [LAN] Starting backend on 0.0.0.0:8000 ...
echo [LAN] Starting frontend on 0.0.0.0:5173 ...
echo.
echo [LAN] Share this URL with devices in same network:
echo [LAN]   Frontend: http://%LOCAL_IP%:5173
echo [LAN]   Backend : http://%LOCAL_IP%:8000
echo.
echo [Tip] If others still cannot access, allow ports 8000/5173 in Windows Firewall.
start "OnlineExam Backend (LAN)" cmd /k "cd /d backend && call start-lan-backend.cmd %LOCAL_IP%"
start "OnlineExam Frontend (LAN)" cmd /k "cd /d frontend && call start-lan-frontend.cmd %LOCAL_IP%"

endlocal
