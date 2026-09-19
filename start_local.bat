@echo off
title NowCast Fusion Launcher
cd /d "%~dp0"
echo ===================================================
echo   NowCast Fusion - Live Radar Convective EWS
echo   Starting Local Stack (FastAPI + React Dashboard)
echo ===================================================

echo [1/2] Starting FastAPI Backend on 0.0.0.0:8000 (Live Radar Mode)...
start "NowCast Backend (Port 8000)" cmd /k "python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies. This may take a minute...
    pushd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Please ensure Node.js is installed.
        popd
        pause
        exit /b 1
    )
    popd
)

echo [2/2] Starting React Dashboard on 0.0.0.0:5173...
start "NowCast React Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo   Live Radar Stack is running!
echo   Dashboard: http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo.
echo   For Wi-Fi/LAN access on phones, run: python scripts\launch_network.py
echo   To simulate historical offline events, run: start_simulator.bat
echo ===================================================
pause



