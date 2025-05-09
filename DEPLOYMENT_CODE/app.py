import pandas as pd
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

# Load the trained model
model = joblib.load("models/k8s_failure_model.pkl")

app = FastAPI()

# Define request model
class PredictionRequest(BaseModel):
    cpu_usage: float
    memory_usage: float
    container_network_receive_bytes_total: float
    container_network_transmit_bytes_total: float
    container_fs_usage_bytes: float
    cpu_usage_avg: float
    memory_usage_avg: float
    container_network_receive_bytes_total_avg: float
    container_network_transmit_bytes_total_avg: float
    container_fs_usage_bytes_avg: float
    container_restart_count_avg: float

@app.post("/predict")
async def predict_failure(data: PredictionRequest):
    # Convert request data to a DataFrame
    input_data = pd.DataFrame([data.dict()])

    # Temporary fix: Add a dummy 'target_avg' column
    input_data["target_avg"] = 0  

    # Make prediction
    prediction = model.predict(input_data)
    
    return {"failure_predicted": "YES" if prediction[0] == 1 else "NO"}

