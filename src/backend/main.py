import os
import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="NowCast Fusion API")

# ==========================================
# 1. Re-define the Model Structure
# ==========================================
class SimpleNowcastCNN(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, out_channels, kernel_size=3, padding=1),
            nn.ReLU()
        )
    def forward(self, x):
        return self.net(x)

# ==========================================
# 2. Load Assets into Memory on Startup
# ==========================================
model = None
dataset = None
current_time_step = 0
MAX_VAL = 1.0

@app.on_event("startup")
def load_assets():
    global model, dataset, MAX_VAL
    
    print("Loading historical data and trained model...")
    # Load dataset
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/assam_gpm_sample.npy'))
    if os.path.exists(data_path):
        raw_data = np.load(data_path)
        MAX_VAL = np.max(raw_data)
        dataset = raw_data / MAX_VAL if MAX_VAL > 0 else raw_data
        print(f"Data loaded. Max precipitation: {MAX_VAL} mm/hr")
        
    # Load model
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../engine/nowcast_model.pth'))
    if os.path.exists(model_path):
        model = SimpleNowcastCNN(in_channels=3, out_channels=3)
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval() # Set to evaluation mode
        print("AI Model loaded successfully.")

# ==========================================
# 3. API Endpoints
# ==========================================
@app.get("/")
def health_check():
    return {"status": "ok", "message": "NowCast Backend Running."}

@app.get("/api/v1/forecast/latest")
def get_forecast():
    """
    Simulates a live data stream. 
    Grabs the 'current' 3 frames, passes them through the AI model, 
    and returns the prediction alongside the current frame.
    """
    global current_time_step
    
    if dataset is None or model is None:
        return {"error": "Model or Data not found. Did you run the training script?"}
        
    # If we reach the end of our historical data, loop back to the start
    if current_time_step + 3 >= len(dataset):
        current_time_step = 0 
        
    # Get the past 1.5 hours of weather (3 frames)
    past_frames = dataset[current_time_step : current_time_step + 3]
    
    # Run the AI Inference!
    with torch.no_grad():
        # PyTorch expects shape: (Batch, Channels, Height, Width)
        x_tensor = torch.FloatTensor(past_frames).unsqueeze(0) 
        prediction = model(x_tensor)
        predicted_frames = prediction.squeeze(0).numpy()
    
    # Advance the simulator clock for the next time the dashboard refreshes
    current_time_step += 1
    
    # We send back the very last 'current' frame, and the first 'predicted' frame (+30 mins)
    # We multiply by MAX_VAL to convert back from normalized (0-1) to mm/hr
    return {
        "current_rain_map": (past_frames[-1] * MAX_VAL).tolist(),
        "predicted_rain_map": (predicted_frames[0] * MAX_VAL).tolist(),
        "time_step": current_time_step
    }
