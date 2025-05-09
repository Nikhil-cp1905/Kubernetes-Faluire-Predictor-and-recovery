# scripts/predictgemini.py
import pandas as pd
import numpy as np
import joblib
from sklearn.impute import SimpleImputer

# Paths
CSV_PATH = "/home/pavithra/k8s-failure-prediction/data/k8s_live_metrics.csv"
MODEL_PATH = "../models/k8s_failure_model_live.pkl"
OUTPUT_PATH = "output.csv"

# Load data
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip().str.replace(r'\s+', '_', regex=True).str.lower()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)

# Compute rolling averages for numeric columns
numeric_cols = df.select_dtypes(include=[np.number]).columns
for col in numeric_cols:
    if f"{col}_avg" not in df.columns:
        df[f"{col}_avg"] = df[col].rolling(window=5, min_periods=1).mean()

# Drop non-numeric columns
df = df.select_dtypes(include=[np.number])

# Impute missing values
imputer = SimpleImputer(strategy="mean")
df_imputed = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)

# Load trained model
model = joblib.load(MODEL_PATH)

# Predict
predictions = model.predict(df_imputed)
df_output = df_imputed.copy()
df_output["prediction"] = predictions

# Save to output.csv
df_output.to_csv(OUTPUT_PATH, index=False)
print(f"✅ Predictions saved to {OUTPUT_PATH}")

