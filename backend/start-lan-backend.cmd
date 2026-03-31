@echo off
setlocal

set "LOCAL_IP=%~1"
if "%LOCAL_IP%"=="" set "LOCAL_IP=127.0.0.1"

set "DJANGO_ALLOWED_HOSTS=*"

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

echo [Backend] Local URL:   http://127.0.0.1:8000
echo [Backend] LAN URL:     http://%LOCAL_IP%:8000
echo [Backend] AllowedHost: %DJANGO_ALLOWED_HOSTS%
echo.

%PY_EXE% manage.py runserver 0.0.0.0:8000

endlocal
