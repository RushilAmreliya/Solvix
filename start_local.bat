@echo off
title NowCast Fusion Launcher
echo ===================================================
echo   NowCast Fusion - Convective Hazard Nowcasting
echo   Starting Local Development Stack (React + FastAPI)
echo ===================================================

echo [1/3] Starting FastAPI Backend on http://localhost:8000...
start "NowCast Backend (Port 8000)" cmd /k "python -m uvicorn backend.main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Data Simulator (60 FPS)...
start "NowCast Simulator (60 FPS)" cmd /k "python -m backend.simulator --fps 60 --loop"

timeout /t 2 /nobreak >nul

echo [3/3] Starting React Dashboard on http://localhost:5173...
start "NowCast React Frontend" cmd /k "cd frontend && npm run dev"

echo ===================================================
echo   All 3 services are running!
echo   Open your browser at: http://localhost:5173
echo ===================================================
pause
