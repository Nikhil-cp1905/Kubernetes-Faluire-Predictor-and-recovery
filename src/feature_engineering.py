import pandas as pd
import os

# Load CPU and Memory Data
cpu_df = pd.read_csv("data/cpu_usage.csv")
memory_df = pd.read_csv("data/memory_usage.csv")

# Convert timestamps to datetime
cpu_df["timestamp"] = pd.to_datetime(cpu_df["timestamp"])
memory_df["timestamp"] = pd.to_datetime(memory_df["timestamp"])

# Ensure column names are correct
print("CPU Columns:", cpu_df.columns)
print("Memory Columns:", memory_df.columns)

# Assign correct column names
cpu_column = "cpu_usage" if "cpu_usage" in cpu_df.columns else "value"
memory_column = "memory_usage" if "memory_usage" in memory_df.columns else "value"

# Compute CPU and Memory rate of change
cpu_df["cpu_rate"] = cpu_df[cpu_column].diff() / cpu_df["timestamp"].diff().dt.total_seconds()
memory_df["memory_rate"] = memory_df[memory_column].diff() / memory_df["timestamp"].diff().dt.total_seconds()

# Save individual feature files
cpu_df.to_csv("data/cpu_features.csv", index=False)
memory_df.to_csv("data/memory_features.csv", index=False)

# Merge CPU and Memory Data on Timestamp
merged_df = pd.merge(cpu_df, memory_df, on="timestamp", how="inner")

# Add Failure Label (Synthetic)
failure_threshold_cpu = 0.9  # Adjust as needed
failure_threshold_memory = 0.9  # Adjust as needed

merged_df["failure"] = (
    (merged_df["cpu_rate"] > failure_threshold_cpu) | 
    (merged_df["memory_rate"] > failure_threshold_memory)
).astype(int)

# Handle NaN and Inf values
merged_df.replace([float("inf"), float("-inf")], float("nan"), inplace=True)
merged_df.fillna(0, inplace=True)

# Save Processed Data
processed_data_path = "data/processed_metrics.csv"
os.makedirs("data", exist_ok=True)  # Ensure directory exists
merged_df.to_csv(processed_data_path, index=False)

print(f"✅ Feature engineering completed! Processed data saved to {processed_data_path}")

