import os
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from train import FEATURE_COLUMNS, TARGET_COLUMN, perform_stratified_group_chronological_split

FEATURES_CSV = os.path.join("data", "processed", "features.csv")
MODEL_PATH = os.path.join("models", "gateguard_model.pkl")
METRICS_TXT_PATH = os.path.join("models", "metrics.txt")


def main():
    print("=== GateGuard Model Evaluation Script ===")

    # 1. Load trained model artifact
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}. Run src/train.py first.")

    model = joblib.load(MODEL_PATH)
    print(f"[*] Loaded model artifact from {MODEL_PATH}")

    # 2. Load dataset and reproduce held-out test split
    if not os.path.exists(FEATURES_CSV):
        raise FileNotFoundError(f"Features dataset not found at {FEATURES_CSV}")

    df = pd.read_csv(FEATURES_CSV)
    train_df, test_df = perform_stratified_group_chronological_split(df, train_ratio=0.8)

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    train_size = len(train_df)
    test_size = len(test_df)
    num_malicious = (y_test == 1).sum()
    num_benign = (y_test == 0).sum()

    # 3. Predict on held-out test set
    y_pred = model.predict(X_test)

    # 4. Compute metrics
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    report_str = classification_report(y_test, y_pred, labels=[0, 1], target_names=["Benign", "Malicious"])

    # 5. Format clean summary text
    note_line = f"Evaluated on N={test_size} test samples ({num_malicious} malicious, {num_benign} benign), synthetic + CSIC 2010 + OWASP SecLists dataset."

    metrics_content = f"""================ GATEGUARD MODEL METRICS REPORT ================

{note_line}

Dataset Partitioning:
  - Total Samples     : {len(df)}
  - Train Set Size    : {train_size} ({len(train_df)/len(df)*100:.2f}%)
  - Test Set Size     : {test_size} ({len(test_df)/len(df)*100:.2f}%)

Overall Performance:
  - Accuracy          : {acc:.4f} ({acc*100:.2f}%)

Confusion Matrix:
  [[TN FP] [FN TP]]
  {cm.tolist()}

Classification Report:
{report_str}
=================================================================
"""

    # 6. Save to models/metrics.txt
    os.makedirs("models", exist_ok=True)
    with open(METRICS_TXT_PATH, "w", encoding="utf-8") as f:
        f.write(metrics_content)

    print(f"[+] Saved evaluation report to {METRICS_TXT_PATH}")
    print("\n" + metrics_content)


if __name__ == "__main__":
    main()
