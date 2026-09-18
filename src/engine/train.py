import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# ==========================================
# 1. Dataset Definition
# ==========================================
class WeatherDataset(Dataset):
    def __init__(self, data_path, seq_in=3, seq_out=3):
        """
        seq_in: Number of past frames to look at (e.g., 3 frames = 1.5 hours)
        seq_out: Number of future frames to predict (e.g., 3 frames = 1.5 hours ahead)
        """
        print(f"Loading data from {data_path}...")
        self.data = np.load(data_path)
        
        # Normalize the data (Precipitation max is roughly 50-100mm/hr)
        # For Neural Networks, keeping values between 0 and 1 is crucial
        self.max_val = np.max(self.data)
        if self.max_val > 0:
            self.data = self.data / self.max_val
            
        self.seq_in = seq_in
        self.seq_out = seq_out
        self.total_seq = seq_in + seq_out
        print(f"Dataset shape: {self.data.shape}. Max precipitation found: {self.max_val}")

    def __len__(self):
        # We can't take sequences that go past the end of the array
        return len(self.data) - self.total_seq

    def __getitem__(self, idx):
        # Input (X): Past 'seq_in' frames
        x = self.data[idx : idx + self.seq_in]
        # Target (Y): Future 'seq_out' frames
        y = self.data[idx + self.seq_in : idx + self.total_seq]
        return torch.FloatTensor(x), torch.FloatTensor(y)

# ==========================================
# 2. Model Definition
# ==========================================
class SimpleNowcastCNN(nn.Module):
    """
    A lightweight Convolutional Neural Network for Spatiotemporal prediction.
    Instead of a heavy ConvLSTM, this treats the sequence of past frames as 'channels'.
    Very fast to train on laptops and perfect for hackathon prototypes!
    """
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
            nn.ReLU() # ReLU ensures we don't predict negative rain!
        )
        
    def forward(self, x):
        return self.net(x)

# ==========================================
# 3. Training Loop
# ==========================================
def train_model():
    # File paths
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/assam_gpm_sample.npy'))
    model_save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'nowcast_model.pth'))
    
    if not os.path.exists(data_path):
        print(f"Error: Could not find {data_path}. Did you run fetch_gee_data.py?")
        return

    # Hyperparameters
    SEQ_IN = 3   # Look at past 1.5 hours
    SEQ_OUT = 3  # Predict next 1.5 hours
    BATCH_SIZE = 8
    EPOCHS = 10
    LEARNING_RATE = 0.001

    # Load Dataset
    dataset = WeatherDataset(data_path, seq_in=SEQ_IN, seq_out=SEQ_OUT)
    
    # Split into Train (80%) and Test (20%)
    train_size = int(0.8 * len(dataset))
    test_size = len(dataset) - train_size
    train_dataset, test_dataset = torch.utils.data.random_split(dataset, [train_size, test_size])
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # Initialize Model, Loss, and Optimizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")
    
    model = SimpleNowcastCNN(in_channels=SEQ_IN, out_channels=SEQ_OUT).to(device)
    
    # We use Mean Squared Error (MSE) loss
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # Training
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            # 1. Forward pass (Predict future frames)
            predictions = model(batch_x)
            
            # 2. Calculate Loss (How wrong were we?)
            loss = criterion(predictions, batch_y)
            
            # 3. Backward pass (Update weights)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        avg_loss = running_loss / len(train_loader)
        print(f"Epoch [{epoch+1}/{EPOCHS}] - Loss: {avg_loss:.6f}")

    # Save the trained model
    torch.save(model.state_dict(), model_save_path)
    print(f"✅ Training Complete! Model saved to {model_save_path}")

if __name__ == "__main__":
    train_model()
