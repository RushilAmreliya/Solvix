@echo off
title PERSIANN-CCS Smart Satellite Data Downloader
echo ======================================================================
echo   NowCast Fusion - Smart Convective Data Downloader
echo   Coverage: May 1, 2023 to July 31, 2026
echo   Strategy: Continuous Monsoon + Off-Season Storms (+3h/-2h buffer)
echo ======================================================================
echo.
echo Starting download process in background...
echo (It saves progress year-by-year; you can pause and resume anytime)
echo.

python -m backend.engine.fetch_persiann --start 2023-05-01 --end 2026-07-31

echo.
echo ======================================================================
echo   Download Finished! 
echo   Consolidated dataset saved to data\assam_persiann_4km.npy
echo ======================================================================
pause
