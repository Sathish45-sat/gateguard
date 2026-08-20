import os
import joblib
import pandas as pd

from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier

FEATURES_CSV = os.path.join("data", "processed", "features.csv")
MODELS_DIR = "models"
MODEL_PATH = os.path.join(MODELS_DIR, "gateguard_model.pkl")

FEATURE_COLUMNS = ["entropy", "length", "keyword_count", "special_char_ratio"]
TARGET_COLUMN = "label"


def perform_stratified_group_chronological_split(df: pd.DataFrame, train_ratio: float = 0.8):
    """
    Split dataset chronologically by base_sample_id groups, stratified by class label:
    - Never splits any base_sample_id across train and test sets.
    - Preserves class balance by performing chronological group splits within benign (0) and malicious (1) groups separately.
    """
    train_dfs = []
    test_dfs = []

    for label_val in [0, 1]:
        sub_df = df[df["label"] == label_val].copy()

        # Compute min timestamp and row count per group for this class
        group_stats = (
            sub_df.groupby("base_sample_id")
            .agg(min_ts=("timestamp", "min"), group_size=("timestamp", "count"))
            .reset_index()
        )

        # Sort groups chronologically by earliest timestamp
        group_stats = group_stats.sort_values(by="min_ts").reset_index(drop=True)

        total_rows = len(sub_df)
        target_train_rows = total_rows * train_ratio

        accumulated_rows = 0
        train_group_ids = []
        test_group_ids = []

        for _, row in group_stats.iterrows():
            gid = row["base_sample_id"]
            gsize = row["group_size"]

            if accumulated_rows < target_train_rows:
                train_group_ids.append(gid)
                accumulated_rows += gsize
            else:
                test_group_ids.append(gid)

        train_dfs.append(sub_df[sub_df["base_sample_id"].isin(train_group_ids)])
        test_dfs.append(sub_df[sub_df["base_sample_id"].isin(test_group_ids)])

    train_df = pd.concat(train_dfs, ignore_index=True)
    test_df = pd.concat(test_dfs, ignore_index=True)

    # Verify zero base_sample_id leakage
    overlap = set(train_df["base_sample_id"]).intersection(set(test_df["base_sample_id"]))
    assert len(overlap) == 0, f"ERROR: Group leakage detected for base_sample_ids: {overlap}"

    return train_df, test_df


def main():
    print("=== GateGuard XGBoost Model Training (Group-Based Chronological Split) ===")

    if not os.path.exists(FEATURES_CSV):
        raise FileNotFoundError(f"Dataset not found at {FEATURES_CSV}")

    df = pd.read_csv(FEATURES_CSV)
    print(f"[*] Loaded dataset: {len(df)} total rows across {df['base_sample_id'].nunique()} unique base_sample_ids.")

    print("\n--- Performing Stratified Group-Based Chronological Train/Test Split ---")
    train_df, test_df = perform_stratified_group_chronological_split(df, train_ratio=0.8)

    train_pct = (len(train_df) / len(df)) * 100
    test_pct = (len(test_df) / len(df)) * 100

    print(f"Train Set : {len(train_df)} rows ({train_pct:.2f}%) across {train_df['base_sample_id'].nunique()} base_sample_ids")
    print(f"Test Set  : {len(test_df)} rows ({test_pct:.2f}%) across {test_df['base_sample_id'].nunique()} base_sample_ids")
    print(f"Train Class Dist : Benign: {(train_df['label']==0).sum()}, Malicious: {(train_df['label']==1).sum()}")
    print(f"Test Class Dist  : Benign: {(test_df['label']==0).sum()}, Malicious: {(test_df['label']==1).sum()}")
    print("[CONFIRMED] ZERO base_sample_id overlap between train and test splits.")

    # Features & targets
    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    # Class imbalance weighting
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    scale_pos_weight = num_neg / num_pos if num_pos > 0 else 1.0

    print(f"\n[*] Train scale_pos_weight: {scale_pos_weight:.4f}")

    # Train model
    print("\n[*] Training XGBoost Classifier...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    # Evaluation
    print("\n================ MODEL EVALUATION (NON-LEAKED TEST SET) ================")
    y_pred = model.predict(X_test)

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    print(cm)

    print("\nClassification Report:")
    report = classification_report(y_test, y_pred, labels=[0, 1], target_names=["Benign", "Malicious"])
    print(report)

    # Save model artifact
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"[+] Saved trained model artifact to {MODEL_PATH}")
    print("=============================================================")


if __name__ == "__main__":
    main()
