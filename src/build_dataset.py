import os
import random
import time
import pandas as pd
from features import extract_features

RAW_DIR = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")

RAW_MALICIOUS_PATH = os.path.join(RAW_DIR, "malicious_raw.csv")
OBFUSCATED_MALICIOUS_PATH = os.path.join(PROCESSED_DIR, "malicious_obfuscated.csv")
RAW_BENIGN_PATH = os.path.join(RAW_DIR, "benign_raw.csv")
OUTPUT_FEATURES_PATH = os.path.join(PROCESSED_DIR, "features.csv")


def load_all_datasets() -> pd.DataFrame:
    """Load and combine datasets while preserving base_sample_id."""
    dfs = []

    if os.path.exists(RAW_MALICIOUS_PATH):
        dfs.append(pd.read_csv(RAW_MALICIOUS_PATH))
    if os.path.exists(OBFUSCATED_MALICIOUS_PATH):
        dfs.append(pd.read_csv(OBFUSCATED_MALICIOUS_PATH))
    if os.path.exists(RAW_BENIGN_PATH):
        dfs.append(pd.read_csv(RAW_BENIGN_PATH))

    if not dfs:
        raise FileNotFoundError("No input dataset CSV files found in data/raw or data/processed.")

    combined_df = pd.concat(dfs, ignore_index=True)
    # Deduplicate based on request_string and label
    combined_df = combined_df.drop_duplicates(subset=["request_string", "label"]).reset_index(drop=True)
    return combined_df


def assign_synthetic_sessions_and_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Assign synthetic session_id and monotonic timestamps."""
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    session_ids = []
    timestamps = []

    current_session_num = 1
    requests_in_current_session = random.randint(3, 8)
    current_session_count = 0

    base_time = int(time.time()) - (len(df) * 5)

    for i in range(len(df)):
        sess_id = f"sess_{current_session_num:04d}"
        session_ids.append(sess_id)

        base_time += random.randint(1, 5)
        timestamps.append(base_time)

        current_session_count += 1
        if current_session_count >= requests_in_current_session:
            current_session_num += 1
            requests_in_current_session = random.randint(3, 8)
            current_session_count = 0

    df["session_id"] = session_ids
    df["timestamp"] = timestamps
    return df


def main():
    print("=== GateGuard Feature Extraction & Dataset Builder ===")

    # 1. Load data
    df = load_all_datasets()
    print(f"[*] Loaded {len(df)} total unique request strings.")

    # 2. Extract features
    print("[*] Extracting features (entropy, length, keyword_count, special_char_ratio)...")
    feature_list = []
    for req in df["request_string"]:
        feats = extract_features(req)
        feature_list.append(feats)

    features_df = pd.DataFrame(feature_list)

    # 3. Combine features with label and base_sample_id
    full_df = pd.concat([features_df, df[["label", "base_sample_id"]]], axis=1)

    # 4. Assign synthetic session_id and timestamps
    full_df = assign_synthetic_sessions_and_timestamps(full_df)

    # Reorder columns explicitly according to contract
    ordered_cols = [
        "entropy", "length", "keyword_count", "special_char_ratio",
        "label", "base_sample_id", "session_id", "timestamp"
    ]
    full_df = full_df[ordered_cols]

    # 5. Export features CSV
    full_df.to_csv(OUTPUT_FEATURES_PATH, index=False)
    print(f"[+] Successfully generated features dataset at {OUTPUT_FEATURES_PATH}")

    # 6. Summary stats
    print("\n================ DATASET SUMMARY ================")
    print(f"Total Rows: {len(full_df)}")
    print(f"Unique base_sample_ids: {full_df['base_sample_id'].nunique()}")
    print("\nClass Balance:")
    class_counts = full_df["label"].value_counts().to_dict()
    print(f"  Benign (label 0):    {class_counts.get(0, 0)}")
    print(f"  Malicious (label 1): {class_counts.get(1, 0)}")
    print("\n5 Sample Rows:")
    print(full_df.head(5).to_string(index=False))
    print("==================================================")


if __name__ == "__main__":
    main()
