@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Solvix local-network launcher
REM Starts the backend, demo simulator, and Vite frontend in separate windows.

cd /d "%~dp0"

if not exist "backend\main.py" (
    echo [ERROR] Could not find backend\main.py.
    echo Put this file in the root of the Solvix repository.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] Could not find frontend\package.json.
    echo Put this file in the root of the Solvix repository.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python and enable "Add Python to PATH".
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH.
    echo Install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Detect the first usable private IPv4 address.
set "LAN_IP="
for /f "delims=" %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } ^| Select-Object -First 1 -ExpandProperty IPAddress"') do set "LAN_IP=%%I"

if not defined LAN_IP set "LAN_IP=localhost"

if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies. This may take a minute...
    pushd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        popd
        pause
        exit /b 1
    )
    popd
)

echo.
echo ============================================================
echo  SOLVIX - LOCAL NETWORK MODE
echo ============================================================
echo  This computer: http://localhost:5173
echo  Other devices: http://%LAN_IP%:5173
echo  Backend API:   http://%LAN_IP%:8000/docs
echo.
echo  Keep all three command windows open while using Solvix.
echo  Both devices must be connected to the same Wi-Fi/LAN.
echo ============================================================
echo.

start "Solvix Backend - port 8000" cmd /k "cd /d "%~dp0" && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

start "Solvix Demo Simulator" cmd /k "cd /d "%~dp0" && python -m backend.simulator --source satellite --fps 60 --loop"

start "Solvix Frontend - port 5173" cmd /k "cd /d "%~dp0frontend" && set VITE_API_URL=http://%LAN_IP%:8000 && call npm run dev -- --host 0.0.0.0 --port 5173"

timeout /t 3 /nobreak >nul

start "Solvix Dashboard" "http://localhost:5173"

echo.
echo [READY] Open this URL on another device:
echo         http://%LAN_IP%:5173
echo.
echo If Windows Firewall asks, allow Python and Node.js on Private networks.
echo.
pause
endlocal
