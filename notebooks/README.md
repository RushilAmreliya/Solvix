# Notebooks

This directory contains interactive Jupyter notebooks for training, exploratory data analysis, and experimentation.

## Files

- `train_on_colab.ipynb`: Complete Google Colab notebook for training the `UNetNowcast` model with PyTorch, custom `RainWeightedLoss`, and stratified data sampling.

## Running on Google Colab

1. Open [Google Colab](https://colab.research.google.com/).
2. Select **Upload** and upload `notebooks/train_on_colab.ipynb`.
3. In Colab, enable a GPU runtime via **Runtime > Change runtime type > GPU (T4 or higher)**.
4. Upload your dataset (or clone the repository):
   ```bash
   !git clone https://github.com/RushilAmreliya/Solvix.git
   %cd Solvix
   !pip install -r requirements.txt
   ```
5. Follow the step-by-step cells in the notebook to train the model, evaluate Critical Success Index (CSI) and Equitable Threat Score (ETS), and export the trained weights (`nowcast_model.pth`).
