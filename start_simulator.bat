@echo off
title NowCast Fusion — Historical Event Simulator
cd /d "%~dp0"
echo ===================================================
echo   NowCast Fusion — Historical Storm Simulator
echo   Replaying Assam Squall Line (May 2023) at 60 FPS
echo ===================================================
echo.
echo Make sure the backend is running first (start_local.bat).
echo Streaming historical radar frames to http://localhost:8000/api/v1/ingest ...
echo.

python -m backend.simulator --fps 60 --loop
pause
