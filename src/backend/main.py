import os
import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NowCast Fusion API")

# Allow Streamlit Cloud to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/assam_gpm_sample.npy'))
    if os.path.exists(data_path):
        raw_data = np.load(data_path)
        MAX_VAL = np.max(raw_data)
        dataset = raw_data / MAX_VAL if MAX_VAL > 0 else raw_data
        print(f"Data loaded. Max precipitation: {MAX_VAL} mm/hr")

    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../engine/nowcast_model.pth'))
    if os.path.exists(model_path):
        model = SimpleNowcastCNN(in_channels=3, out_channels=3)
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
        print("AI Model loaded successfully.")

# ==========================================
# 3. API Endpoints
# ==========================================
@app.get("/")
def health_check():
    return {"status": "ok", "message": "NowCast Backend Running."}

@app.get("/api/v1/forecast/latest")
def get_forecast():
    global current_time_step

    if dataset is None or model is None:
        return {"error": "Model or Data not found. Did you run the training script and commit the files?"}

    if current_time_step + 3 >= len(dataset):
        current_time_step = 0

    past_frames = dataset[current_time_step : current_time_step + 3]

    with torch.no_grad():
        x_tensor = torch.FloatTensor(past_frames).unsqueeze(0)
        prediction = model(x_tensor)
        predicted_frames = prediction.squeeze(0).numpy()

    current_time_step += 1

    return {
        "current_rain_map": (past_frames[-1] * MAX_VAL).tolist(),
        "predicted_rain_map": (predicted_frames[0] * MAX_VAL).tolist(),
        "time_step": current_time_step
    }
