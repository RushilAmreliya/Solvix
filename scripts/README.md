# Utility Scripts

This directory contains standalone operational scripts for credentials setup and satellite data acquisition.

## Scripts

### 1. `setup_credentials.py`
Configures authentication credentials for NASA Earthdata (saved securely to user `~/.netrc` / `~/_netrc`).
- **Usage**:
  ```bash
  python scripts/setup_credentials.py
  ```

### 2. `start_download.bat`
Automated batch script to download multi-year PERSIANN-CCS satellite precipitation cubes for Assam.
- **Coverage**: May 1, 2023 to July 31, 2026.
- **Usage**:
  Double-click `scripts/start_download.bat` or run:
  ```bash
  scripts\start_download.bat
  ```
