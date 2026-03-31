@echo off
setlocal

set "LOCAL_IP=%~1"
if "%LOCAL_IP%"=="" set "LOCAL_IP=127.0.0.1"

set "VITE_API_BASE_URL=http://%LOCAL_IP%:8000/api"

echo [Frontend] Local URL:   http://127.0.0.1:5173
echo [Frontend] LAN URL:     http://%LOCAL_IP%:5173
echo [Frontend] API URL:     %VITE_API_BASE_URL%
echo.

npm.cmd run dev -- --host 0.0.0.0 --port 5173

endlocal
