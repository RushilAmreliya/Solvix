import ee
import os
import numpy as np
from datetime import datetime, timedelta

def initialize_gee():
    """Initialize Google Earth Engine."""
    try:
        ee.Initialize()
        print("✅ GEE Initialized Successfully.")
    except ee.ee_exception.EEException as e:
        if 'no project found' in str(e).lower():
            print("\n⚠️ Google Earth Engine now requires a Cloud Project ID.")
            print("You can find this by going to https://code.earthengine.google.com/")
            print("Click your profile icon in the top right - it will say 'Project: your-project-id'")
            project_id = input("\nEnter your GEE Project ID (e.g., ee-yourname): ").strip()
            
            try:
                ee.Initialize(project=project_id)
                print(f"✅ GEE Initialized Successfully with project '{project_id}'.")
            except Exception as inner_e:
                print("❌ Failed to initialize with that project ID.")
                raise inner_e
        else:
            raise e
    except Exception as e:
        print("❌ GEE Initialization failed. Did you run authentication?")
        raise e

def fetch_gpm_data_for_assam(start_date, end_date, output_file):
    """
    Fetches NASA GPM IMERG Half-hourly precipitation data for Assam.
    """
    print(f"Fetching GPM data from {start_date} to {end_date}...")
    
    # Bounding box for Assam and surrounding North-East India
    assam_bbox = ee.Geometry.Rectangle([89.8, 24.0, 96.0, 28.0])
    
    # Load NASA GPM IMERG dataset (Half-hourly)
    collection = (ee.ImageCollection("NASA/GPM_L3/IMERG_V06")
                  .filterBounds(assam_bbox)
                  .filterDate(start_date, end_date)
                  .select('precipitationCal')) # Calibration precipitation in mm/hr

    # Check how many images we found
    count = collection.size().getInfo()
    print(f"Found {count} half-hourly frames in this time range.")
    
    if count == 0:
        print("No data found. Exiting.")
        return

    # Convert the collection to a list to iterate through
    img_list = collection.toList(count)
    
    frames = []
    
    for i in range(count):
        img = ee.Image(img_list.get(i))
        
        try:
            # sampleRectangle gets the raw pixel 2D array directly (bypassing GeoTIFF zips!)
            band_arrs = img.sampleRectangle(region=assam_bbox, defaultValue=0.0)
            precip_list = band_arrs.get('precipitationCal').getInfo()
            array = np.array(precip_list, dtype=float)
            frames.append(array)
        except Exception as e:
            print(f"Skipping frame {i+1} due to error: {e}")
            continue
                
        if (i+1) % 24 == 0:
            print(f"Downloaded {i+1}/{count} frames...")

    if not frames:
        print("No valid frames were downloaded.")
        return

    # Stack into a 3D numpy array (Time, Height, Width)
    data_cube = np.stack(frames)
    
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the numpy array to disk
    np.save(output_file, data_cube)
    print(f"✅ Successfully saved dataset of shape {data_cube.shape} to {output_file}")

if __name__ == "__main__":
    initialize_gee()
    
    # For testing, let's pull 1 week of intense pre-monsoon weather in 2023
    # Once this works, you can change the dates to pull 2020-present in batches!
    START = '2023-05-01'
    END = '2023-05-07'
    OUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/assam_gpm_sample.npy'))
    
    fetch_gpm_data_for_assam(START, END, OUT_PATH)
