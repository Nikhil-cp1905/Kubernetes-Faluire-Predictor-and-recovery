import pandas as pd
import numpy as np
import os
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from imblearn.over_sampling import BorderlineSMOTE
from xgboost import XGBClassifier
from sklearn.impute import SimpleImputer

# CSV path
CSV_PATH = "/home/pavithra/k8s-failure-prediction/data/k8s_live_metrics.csv"
df = pd.read_csv(CSV_PATH)

# Clean column names
df.columns = df.columns.str.strip().str.replace(r'\s+', '_', regex=True).str.lower()

# Convert timestamp and set index
df["timestamp"] = pd.to_datetime(df["timestamp"])
df.set_index("timestamp", inplace=True)

# Compute rolling averages only on numeric columns (if not already present)
numeric_cols = df.select_dtypes(include=[np.number]).columns
for col in numeric_cols:
    if f"{col}_avg" not in df.columns:
        df[f"{col}_avg"] = df[col].rolling(window=5, min_periods=1).mean()

# *** Custom Logic for 'target' ***
# Define custom conditions for failure prediction based on metrics such as CPU, Memory, and Restart Counts
# Custom Logic for 'target' variable based on defined thresholds
cpu_threshold = 0.8  # 80% CPU usage
memory_threshold = 100000000  # 100MB memory usage
restart_threshold = 3  # More than 3 restarts indicating failure# Create a boolean condition for failure based on rolling averages or specific thresholds
df['cpu_failure'] = df['cpu_usage'].rolling(window=2).apply(lambda x: np.any(x > cpu_threshold), raw=True).fillna(False)
df['memory_failure'] = df['memory_usage'].rolling(window=2).apply(lambda x: np.any(x > memory_threshold), raw=True).fillna(False)
df['restart_failure'] = df['container_restarts_avg'].rolling(window=2).apply(lambda x: np.any(x > restart_threshold), raw=True).fillna(False)

# Combine these conditions to form the target variable (1: Failure, 0: Normal)

df['target'] = ((df['cpu_failure'] > 0) | (df['memory_failure'] > 0) | (df['restart_failure'] > 0)).astype(int)
# Drop non-numeric columns like 'instance'
df = df.select_dtypes(include=[np.number])

# Handle missing values (NaNs) by imputation (you can also drop rows with NaNs if you prefer)
imputer = SimpleImputer(strategy="mean")  # Use mean imputation
df_imputed = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)

# Split features and target
X = df_imputed.drop(columns=["target"])
y = df_imputed["target"]

# Handle class imbalance with BorderlineSMOTE
# Check class distribution before applying SMOTE
print("Class distribution before resampling:\n", y.value_counts())

# Handle class imbalance with BorderlineSMOTE
if y.value_counts().min() >= 5 and len(y.value_counts()) > 1:
    smote = BorderlineSMOTE(sampling_strategy='auto', random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X, y)
    print("\nClass distribution after resampling:\n", y_resampled.value_counts())
else:
    # If there's only one class, don't apply SMOTE
    print("\nClass imbalance issue: One class detected. Using original data.")
    X_resampled, y_resampled = X, y

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

# Model 1: Random Forest
rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_split=20,
    min_samples_leaf=10,
    bootstrap=True,
    random_state=42
)

# Model 2: XGBoost
xgb = XGBClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=7,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    use_label_encoder=False,  # To suppress warnings
    eval_metric='logloss'  # Specify the evaluation metric explicitly
)

# Train models
rf.fit(X_train, y_train)
xgb.fit(X_train, y_train)

# Predict
y_pred_rf = rf.predict(X_test)
y_pred_xgb = xgb.predict(X_test)

# Ensemble prediction
y_pred_ensemble = (y_pred_rf + y_pred_xgb) // 2

# Accuracy
train_acc = rf.score(X_train, y_train) * 100
test_acc = accuracy_score(y_test, y_pred_ensemble) * 100
print(f"\n🎯 Train Accuracy: {train_acc:.2f} %")
print(f"🎯 Test Accuracy: {test_acc:.2f} %")
print("\n🔹 Classification Report:\n", classification_report(y_test, y_pred_ensemble))

# Save model
MODEL_PATH = "../models/k8s_failure_model_live.pkl"
joblib.dump(rf, MODEL_PATH)
model = joblib.load(MODEL_PATH)
print(f"\n✅ Model saved at {MODEL_PATH}")
print("\n📊 Model features:\n", model.feature_names_in_)

# Plot confusion matrix
cm = confusion_matrix(y_test, y_pred_ensemble)
plt.figure(figsize=(6, 4))
sns.heatmap(cm, annot=True, fmt='d', cmap="Blues", xticklabels=["No Failure", "Failure"], yticklabels=["No Failure", "Failure"])
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.show()

# Plot feature importance
feature_importances = pd.DataFrame({'Feature': X_train.columns, 'Importance': rf.feature_importances_})
feature_importances = feature_importances.sort_values(by='Importance', ascending=False).head(15)
plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=feature_importances, palette="viridis")
plt.title("Top 15 Important Features")
plt.show()
