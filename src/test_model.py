import pandas as pd
import joblib

# Load trained model
model = joblib.load("models/failure_predictor.pkl")

# Load test data (without labels)
df = pd.read_csv("data/processed_metrics.csv").drop(columns=["timestamp", "failure"], errors="ignore")

# Predict
predictions = model.predict(df)

# Add predictions to the DataFrame
df["predicted_failure"] = predictions

# Print failure counts
print(df["predicted_failure"].value_counts())

# Save results
df.to_csv("data/predictions.csv", index=False)
print("✅ Predictions saved as data/predictions.csv")

