import streamlit as st
import pandas as pd
import json
import sys
import os
from datetime import datetime
import threading
import time
import subprocess
sys.path.append(os.path.abspath('./src'))
from jsonextractor import solution_implementation
from predictgeministreamlit import run_predictions

# Constants
CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/k8s_live_metrics.csv")

# Streamlit app title
st.title("Kubernetes Failure Prediction App")

# State tracking
if "metrics_fetched" not in st.session_state:
    st.session_state.metrics_fetched = False
if "metrics_in_progress" not in st.session_state:
    st.session_state.metrics_in_progress = False
if "model_trained" not in st.session_state:
    st.session_state.model_trained = False
if "prediction_done" not in st.session_state:
    st.session_state.prediction_done = False

# Function to load metrics from CSV
def load_metrics_from_csv():
    try:
        # Read metrics from the CSV file
        df = pd.read_csv(CSV_PATH)
        if df.empty:
            st.warning("⚠️ The CSV file is empty or does not contain valid data.")
            return pd.DataFrame()
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"❌ Error loading metrics from CSV: {e}")
        return pd.DataFrame()

# Function to fetch and save metrics from CSV
def fetch_and_save_metrics():
    st.session_state.metrics_in_progress = True
    st.info("Loading metrics from CSV... Please wait.")
    
    df = load_metrics_from_csv()

    if df.empty:
        st.warning("⚠️ No metrics available from the CSV.")
        st.session_state.metrics_in_progress = False
        return
    
    # Save metrics to CSV (to keep it consistent with the previous approach)
    save_path = os.path.join(os.path.dirname(CSV_PATH), "k8s_live_metrics_copy.csv")
    df.to_csv(save_path, index=False)
    st.success(f"✅ Metrics loaded from CSV and saved to {save_path}")
    st.session_state.metrics_fetched = True
    st.session_state.metrics_in_progress = False

# Background thread to prompt the user to train the model every 30 seconds
def prompt_train_model():
    while True:
        time.sleep(30)  # Prompt every 30 seconds
        if not st.session_state.model_trained:
            st.info("⏳ It's time to train the model. Please click 'Train Model'.")

# Start background thread for prompting to train the model
if "train_model_thread" not in st.session_state:
    st.session_state.train_model_thread = threading.Thread(target=prompt_train_model, daemon=True)
    st.session_state.train_model_thread.start()

# Manually fetch metrics button
if st.button("🔄 Load Metrics from CSV"):
    if not st.session_state.metrics_in_progress:
        fetch_and_save_metrics()

# Train the model
def train_model():
    if not st.session_state.metrics_fetched:
        st.error("Please load metrics from CSV first.")
        return
    st.session_state.model_trained = False
    with st.spinner("Training model..."):
        subprocess.run(["python3", "src/train_model_live.py"], check=True)
        st.session_state.model_trained = True
    st.success("Model trained successfully!")

# Train model button
if st.button("⚙️ Train Model") and st.session_state.metrics_fetched:
    train_model()

# Visualize output
def visualize_output():
    output_path = os.path.join(os.path.dirname(CSV_PATH), "predictions_output.csv")
    if not os.path.exists(output_path):
        st.error(f"Prediction output not found. Please run prediction first.")
        return

    df_output = pd.read_csv(output_path)
    st.markdown("### Prediction Results")
    st.dataframe(df_output)

    # Download button
    st.download_button(
        label="Download Predictions CSV",
        data=df_output.to_csv(index=False),
        file_name="k8s_failure_predictions.csv",
        mime="text/csv"
    )

# Visualize output button
if st.button("📊 Visualize Output") and st.session_state.model_trained:
    visualize_output()

# Prediction logic with timeout handling
# Prediction logic with timeout handling
def run_prediction():
    if not st.session_state.model_trained:
        st.error("Please train the model first.")
        return
    try:
        with st.spinner("Running prediction..."):
            # Run the prediction script with a timeout of 10 seconds
            result = subprocess.run(["python3", "src/predictgeministreamlit.py"], capture_output=True, text=True, timeout=10)
            
            # Check if the subprocess ran successfully
            if result.returncode == 0:
                # Display the output from the script
                st.session_state.prediction_done = True
                st.success("Prediction complete!")
                st.markdown("### Prediction Output:")
                st.text(result.stdout)  # Displaying the script's output

                # Parse and display structured output if needed
                try:
                    # You can also parse the stdout into a Python object if necessary
                    output_data = result.stdout
                    # Assuming the output is in JSON format (you can modify as per the actual output format)
                    parsed_output = json.loads(output_data)
                    st.json(parsed_output)  # Displaying structured data if the output is JSON
                except json.JSONDecodeError:
                    st.warning("Unable to parse prediction output as JSON.")

            else:
                st.error(f"❌ Error during prediction: {result.stderr}")

    except subprocess.TimeoutExpired:
        st.warning("Prediction timed out after 10 seconds.")
    except subprocess.CalledProcessError as e:
        st.error(f"Error during prediction: {e}")

    # Display output after prediction
    visualize_output()

# Run prediction button
if st.button("🚀 Run Prediction") and st.session_state.model_trained:
    run_prediction()

# Display action statuses
st.markdown(f"Metrics fetched: {'Yes' if st.session_state.metrics_fetched else 'No'}")
st.markdown(f"Model trained: {'Yes' if st.session_state.model_trained else 'No'}")
st.markdown(f"Prediction completed: {'Yes' if st.session_state.prediction_done else 'No'}")
