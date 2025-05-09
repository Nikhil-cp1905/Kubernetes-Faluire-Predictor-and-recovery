import requests
import pandas as pd
import os
from datetime import datetime, timezone
import schedule
import time

#PROMETHEUS_URL = "http://localhost:9090/api/v1/query"  # Update if needed
PROMETHEUS_URL = "http://192.168.49.2:32745/api/v1/query"

METRICS = {
    "cpu_usage": 'rate(container_cpu_usage_seconds_total[1m])',
    "memory_usage": 'container_memory_usage_bytes',
    "network_rx": 'rate(container_network_receive_bytes_total[1m])',
    "network_tx": 'rate(container_network_transmit_bytes_total[1m])',
    "filesystem_usage": 'container_fs_usage_bytes',
    "cpu_usage_avg": 'avg(rate(container_cpu_usage_seconds_total[1m]))',
    "memory_usage_avg": 'avg(container_memory_usage_bytes)',
    "network_rx_avg": 'avg(rate(container_network_receive_bytes_total[1m]))',
    "network_tx_avg": 'avg(rate(container_network_transmit_bytes_total[1m]))',
    "filesystem_usage_avg": 'avg(container_fs_usage_bytes)',
    "container_restarts_avg": 'avg(kube_pod_container_status_restarts_total)'
}

SAVE_DIR = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(SAVE_DIR, exist_ok=True)

def fetch_metric(query, label):
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        data = response.json()
    except Exception as e:
        print(f"❌ Failed to fetch metric {label}: {e}")
        return pd.DataFrame()

    results = []
    for item in data.get("data", {}).get("result", []):
        try:
            timestamp = datetime.fromtimestamp(float(item["value"][0]), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            value = float(item["value"][1])
            entry = {"timestamp": timestamp, label: value}

            # Optional fields
            instance = item["metric"].get("instance")
            container = item["metric"].get("container")

            if instance:
                entry["instance"] = instance
            if container:
                entry["container"] = container

            results.append(entry)
        except Exception as e:
            print(f"❌ Error processing {label}: {e}")

    df = pd.DataFrame(results)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

def fetch_and_save_metrics():
    print(f"\n⏱️ Running fetch at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_data = None

    for key, query in METRICS.items():
        print(f"📡 Fetching {key}...")
        df = fetch_metric(query, key)

        if df.empty:
            print(f"⚠️ No data for {key}, skipping.")
            continue

        # Ensure all columns exist
        if all_data is None:
            all_data = df
        else:
            common_cols = list(set(all_data.columns).intersection(set(df.columns)))
            if "timestamp" not in common_cols:
                print(f"⚠️ No common timestamp found for {key}, skipping merge.")
                continue
            all_data = pd.merge(all_data, df, on=common_cols, how="outer")

    if all_data is not None and not all_data.empty:
        save_path = os.path.join(SAVE_DIR, "k8s_live_metrics.csv")
        all_data.to_csv(save_path, index=False)
        print(f"✅ Saved metrics to {save_path}")
        print(all_data.head())
    else:
        print("⚠️ No metrics fetched.")

# Scheduler
schedule.every(5).minutes.do(fetch_and_save_metrics)

print("🕒 Scheduler started. Fetching metrics every 5 minutes...")

# Initial run
fetch_and_save_metrics()

# Infinite loop
while True:
    schedule.run_pending()
    time.sleep(1)

