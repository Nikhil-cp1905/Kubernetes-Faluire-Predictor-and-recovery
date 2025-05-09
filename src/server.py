from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import requests
import os
import random
import time
import threading
from sklearn.impute import SimpleImputer
import re
from kubernetes import client, config
from jsonextractor import solution_implementation

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
MODEL_PATH = "../models/k8s_failure_model_live.pkl"
CSV_PATH = "../data/k8s_live_metrics.csv"

def emit_log(message):
    """Emit log message to frontend via Socket.IO"""
    socketio.emit('log', {'message': message})
    print(message)  # Still print to console for debugging

try:
    config.load_kube_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    emit_log("✅ Kubernetes configuration loaded")
except Exception as e:
    emit_log(f"❌ Kubernetes config error: {e}")



def get_pod_name_for_deployment(deployment_name, namespace="default"):
    try:
        label_selector = f"app={deployment_name}"  
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        for pod in pods.items:
            if pod.status.phase == "Running":
                return pod.metadata.name
        return pods.items[0].metadata.name if pods.items else None
    except Exception as e:
        emit_log(f"❌ Failed to fetch pod name: {e}")
        return None

def load_and_preprocess_data(csv_path):
    emit_log(f"📊 Loading data from {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.replace(r'\s+', '_', regex=True).str.lower()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    # Rolling averages for all numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if f"{col}_avg" not in df.columns:
            df[f"{col}_avg"] = df[col].rolling(window=5, min_periods=1).mean()

    # Dynamic thresholds
    cpu_threshold = df['cpu_usage'].mean() + 2 * df['cpu_usage'].std()
    memory_threshold = df['memory_usage'].mean() + 2 * df['memory_usage'].std()
    restart_threshold = df['container_restarts_avg'].mean() + 2 * df['container_restarts_avg'].std()

    emit_log(f"📊 Thresholds → CPU: {cpu_threshold:.3f}, Memory: {memory_threshold:.3f}, Restarts: {restart_threshold:.3f}")

    # Failure flags
    df['cpu_failure'] = df['cpu_usage'].rolling(window=2).apply(lambda x: np.any(x > cpu_threshold), raw=True).fillna(False)
    df['memory_failure'] = df['memory_usage'].rolling(window=2).apply(lambda x: np.any(x > memory_threshold), raw=True).fillna(False)
    df['restart_failure'] = df['container_restarts_avg'].rolling(window=2).apply(lambda x: np.any(x > restart_threshold), raw=True).fillna(False)

    df['target'] = ((df['cpu_failure'] > 0) | (df['memory_failure'] > 0) | (df['restart_failure'] > 0)).astype(int)

    return df

def impute_data(df):
    df_numeric = df.select_dtypes(include=[np.number])
    imputer = SimpleImputer(strategy="mean")
    df_imputed = pd.DataFrame(imputer.fit_transform(df_numeric), columns=df_numeric.columns, index=df_numeric.index)
    return df_imputed

def get_remediation_advice(metrics_dict):
    emit_log("🤖 Requesting Gemini remediation advice...")
    prompt = (
        "A failure was detected in a Kubernetes cluster based on the following Prometheus metrics:\n\n"
        + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in metrics_dict.items()) +
        "\n\nProvide only the remediation steps in short, actionable bullet points. Do not explain the issue. Focus on what actions should be taken.")

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        advice = response.json()['candidates'][0]['content']['parts'][0]['text']
        emit_log(f"💡 Gemini advice received: {len(advice)} characters")
        return advice
    except Exception as e:
        emit_log(f"❌ Error from Gemini: {str(e)}")
        return f"❌ Error from Gemini: {str(e)}"

def predict_failures(df, model):
    df_imputed = impute_data(df)
    X = df_imputed.drop(columns=["target"], errors="ignore")
    return model.predict(X)

def parse_gemini_advice_to_json(advice_text, pod_name):
    steps = re.findall(r"\* (.+)", advice_text)
    if not steps:  # Try alternative format
        steps = re.findall(r"- (.+)", advice_text)
    if not steps:  # If still no matches, just use the whole text
        steps = [advice_text]
        
    return {
        "solution_steps": steps,
        "deployment_name": "demo-deployment",
        "namespace": "default",
        "pod_name": pod_name,
        "pod_json": {},  # Optional: use real pod spec if available
        "json_input": {
            "deployment_name": "demo-deployment",
            "namespace": "default",
            "correct_image": "nginx:latest",
            "image_pull_secrets": []
        }
    }

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

@socketio.on('connect')
def handle_connect():
    emit_log("🔌 Client connected to dashboard")

@socketio.on('start_analysis')
def handle_start_analysis():
    emit_log("🚀 Starting Kubernetes Analysis")
    threading.Thread(target=run_analysis).start()

def run_analysis():
    try:
        emit_log("📥 Loading model and data...")
        model = joblib.load(MODEL_PATH)
        df = load_and_preprocess_data(CSV_PATH)

        emit_log("🤖 Running predictions...")
        predictions = predict_failures(df, model)
        
        # Send overall statistics
        total_samples = len(predictions)
        failures = sum(predictions)
        success_rate = ((total_samples - failures) / total_samples) * 100
        
        socketio.emit('stats', {
            'total_samples': total_samples,
            'failures': failures,
            'success_rate': f"{success_rate:.1f}%"
        })
        
        for i, prediction in enumerate(predictions):
            result = "❌ Failure" if prediction == 1 else "✅ No Failure"
            emit_log(f"\nSample {i + 1}: {result}")
            
            # Add delay for UI effect
            time.sleep(0.5)

            if prediction == 1:
                metrics_row = df.iloc[i]
                metrics = {
                    "cpu_usage": round(metrics_row.get("cpu_usage", 0), 3),
                    "memory_usage": round(metrics_row.get("memory_usage", 0), 3),
                    "container_restarts_avg": round(metrics_row.get("container_restarts_avg", 0), 3)
                }
                
                # Send detailed metrics to frontend
                socketio.emit('metrics', {
                    'sample': i + 1,
                    'metrics': metrics
                })

                emit_log("📨 Sending metrics to Gemini...")
                advice_text = get_remediation_advice(metrics)
                emit_log(f"💡 Gemini Suggestion for sample {i + 1}:")
                
                # Send remediation steps to frontend
                steps = re.findall(r"\* (.+)", advice_text)
                if not steps:
                    steps = re.findall(r"- (.+)", advice_text)
                if not steps:
                    steps = [advice_text]
                
                socketio.emit('remediation', {
                    'sample': i + 1,
                    'steps': steps
                })
                
                for step in steps:
                    emit_log(f"  • {step}")
                
                pod_name = get_pod_name_for_deployment("demo-app", "default")
                if not pod_name:
                    emit_log("❌ Pod not found. Skipping remediation for this sample.")
                    continue

                solution_json = parse_gemini_advice_to_json(advice_text, pod_name)
                emit_log("🧩 Parsed solution steps")

                emit_log("🛠️ Running auto-remediation engine...")
                solution_implementation(
                    solution_json.get("solution_steps"),
                    solution_json.get("deployment_name"),
                    solution_json.get("namespace"),
                    solution_json.get("pod_name"),
                    pod_json=solution_json.get("pod_json"),
                    json_input=solution_json.get("json_input"),
                    emit_callback=emit_log  # Pass our emit function
                )
                
                emit_log("✅ Remediation complete for this sample")
                
                # Add delay between samples
                time.sleep(1.5)
                
        emit_log("🏁 Analysis complete!")
        
    except Exception as e:
        emit_log(f"❌ Error in analysis: {str(e)}")

if __name__ == "__main__":
    emit_log("🚀 Starting Kubernetes Auto-Remediation Server")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
