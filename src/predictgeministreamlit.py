import pandas as pd
import numpy as np
import joblib
import requests
import os
from sklearn.impute import SimpleImputer
from jsonextractor import solution_implementation
from kubernetes import client, config
import re
from dotenv import load_dotenv

# Constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY","AIzaSyD9iuKEeITxpZQZLfHFUqiLbZwGAh5mmNg")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
MODEL_PATH = "../models/k8s_failure_model_live.pkl"
CSV_PATH = "../data/k8s_live_metrics.csv"

config.load_kube_config()  # Or config.load_incluster_config() if running inside cluster
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def get_pod_name_for_deployment(deployment_name, namespace="default"):
    try:
        label_selector = f"app={deployment_name}"
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        for pod in pods.items:
            if pod.status.phase == "Running":
                return pod.metadata.name
        return pods.items[0].metadata.name if pods.items else None
    except Exception as e:
        print(f"❌ Failed to fetch pod name: {e}")
        return None

def load_and_preprocess_data(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.replace(r'\s+', '_', regex=True).str.lower()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if f"{col}_avg" not in df.columns:
            df[f"{col}_avg"] = df[col].rolling(window=5, min_periods=1).mean()

    cpu_threshold = df['cpu_usage'].mean() + 2 * df['cpu_usage'].std()
    memory_threshold = df['memory_usage'].mean() + 2 * df['memory_usage'].std()
    restart_threshold = df['container_restarts_avg'].mean() + 2 * df['container_restarts_avg'].std()

    print(f"📊 Thresholds → CPU: {cpu_threshold:.3f}, Memory: {memory_threshold:.3f}, Restarts: {restart_threshold:.3f}")

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
        advice_text = response.json()['candidates'][0]['content']['parts'][0]['text']

        # Filter out irrelevant or empty advice
        if "No predefined solution" in advice_text:
            return None  # Skip and return nothing if the advice isn't relevant

        return advice_text
    except Exception as e:
        return f"❌ Error from Gemini: {str(e)}"

def predict_failures(df, model):
    df_imputed = impute_data(df)
    X = df_imputed.drop(columns=["target"], errors="ignore")
    return model.predict(X)

def parse_gemini_advice_to_json(advice_text, pod_name):
    steps = re.findall(r"\* (.+)", advice_text)
    return {
        "solution_steps": steps,
        "rollback": None,
        "deployment_name": "demo-deployment",
        "namespace": "default",
        "pod_name": pod_name,
        "pod_json": {},
        "json_input": {
            "deployment_name": "demo-deployment",
            "namespace": "default",
            "correct_image": "nginx:latest",
            "image_pull_secrets": []
        }
    }

def run_predictions():
    model = joblib.load(MODEL_PATH)
    df = load_and_preprocess_data(CSV_PATH)
    predictions = predict_failures(df, model)

    results = []

    for i, prediction in enumerate(predictions):
        result = "❌ Failure" if prediction == 1 else "✅ No Failure"
        metrics_row = df.iloc[i]
        metrics = {
            "cpu_usage": round(metrics_row.get("cpu_usage", 0), 3),
            "memory_usage": round(metrics_row.get("memory_usage", 0), 3),
            "container_restarts_avg": round(metrics_row.get("container_restarts_avg", 0), 3)
        }

        advice_text = get_remediation_advice(metrics)
        if not advice_text:  # Skip if advice is empty or irrelevant
            continue
        
        pod_name = get_pod_name_for_deployment("demo-app", "default")
        if not pod_name:
            continue

        solution_json = parse_gemini_advice_to_json(advice_text, pod_name)

        results.append({
            "result": result,
            "metrics": metrics,
            "advice": solution_json
        })

    return results

