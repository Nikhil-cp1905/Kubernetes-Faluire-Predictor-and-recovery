from fastapi import FastAPI
import pickle
import numpy as np

app = FastAPI()

# Load Trained Model
with open("../model/model.pkl", "rb") as file:
    model = pickle.load(file)

@app.get("/predict")
def predict(cpu: float, mem: float):
    prediction = model.predict(np.array([[cpu, mem]]))
    return {"failure_predicted": bool(prediction[0])}

