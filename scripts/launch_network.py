"""
NowCast Fusion — Local Network (LAN) Launcher
Detects your machine's private LAN IPv4 address and starts the FastAPI backend
and Vite frontend configured for cross-device access over Wi-Fi.

Usage:
    python scripts/launch_network.py
"""
import os
import socket
import subprocess
import sys
import time


def get_lan_ip() -> str:
    """Detect private LAN IPv4 address using standard UDP socket (no PowerShell needed)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not send actual traffic; determines default outbound routing interface
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    frontend_dir = os.path.join(root_dir, "frontend")
    lan_ip = get_lan_ip()

    print("=" * 62)
    print("  NOWCAST FUSION — LOCAL WI-FI / NETWORK MODE")
    print("=" * 62)
    print(f"  This computer:  http://localhost:5173")
    print(f"  Phones/Tablets: http://{lan_ip}:5173")
    print(f"  Backend API:    http://{lan_ip}:8000/docs")
    print("=" * 62)
    print("  Keep this terminal open while using NowCast Fusion.")
    print("  Ensure all devices are on the same Wi-Fi network.")
    print("=" * 62)
    print()

    # 1. Install frontend dependencies if missing
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("[INFO] Installing frontend dependencies. This may take a minute...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, shell=True, check=True)

    # 2. Start backend
    print(f"[1/2] Starting FastAPI Backend on 0.0.0.0:8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=root_dir,
    )
    time.sleep(2)

    # 3. Start frontend with VITE_API_URL set to LAN IP
    print(f"[2/2] Starting React Dashboard on 0.0.0.0:5173...")
    env = os.environ.copy()
    env["VITE_API_URL"] = f"http://{lan_ip}:8000"
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
        cwd=frontend_dir,
        env=env,
        shell=True,
    )

    print()
    print(f"[READY] Open this URL on your phone/tablet:")
    print(f"        http://{lan_ip}:5173")
    print()
    print("Press Ctrl+C to stop all services.")

    try:
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down NowCast Fusion...")
        frontend_proc.terminate()
        backend_proc.terminate()
        print("Done.")


if __name__ == "__main__":
    main()
