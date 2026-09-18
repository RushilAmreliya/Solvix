import time
import argparse
from datetime import datetime, timedelta

def main():
    """
    Data Simulator Script.
    Replays a historical severe weather event (e.g., Assam squall line) chronologically.
    It simulates pushing radar and satellite frames to the processing pipeline.
    """
    parser = argparse.ArgumentParser(description="NowCast Fusion Data Simulator")
    parser.add_argument("--event", type=str, default="assam_2023", help="Historical event name to replay")
    parser.add_argument("--interval", type=int, default=10, help="Simulated interval between frames in minutes")
    parser.add_argument("--speed", type=float, default=1.0, help="Playback speed multiplier (1.0 = real-time, 0.1 = 10x faster)")
    
    args = parser.parse_args()
    
    print(f"Starting simulation for event: {args.event}")
    print(f"Simulating a new data frame every {args.interval} minutes...")
    
    # Start time of the simulated event
    simulated_time = datetime(2023, 5, 15, 12, 0, 0)
    
    try:
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Publishing frame for simulated time: {simulated_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # TODO: Implement actual data loading (e.g., read NetCDF/HDF5 via Xarray)
            # TODO: Implement PySTEPS optical flow inference here or trigger it via API
            # TODO: Save output as GeoJSON/Raster to a database or serving directory
            
            # Increment simulated time
            simulated_time += timedelta(minutes=args.interval)
            
            # Wait before publishing next frame (scaled by speed)
            # E.g. 10 mins interval at 0.1 speed = 600 * 0.1 = 60 seconds real wait
            real_wait_seconds = (args.interval * 60) * args.speed
            time.sleep(real_wait_seconds)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped.")

if __name__ == "__main__":
    main()
