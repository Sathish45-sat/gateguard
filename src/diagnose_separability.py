import os
import pandas as pd
from train import perform_stratified_group_chronological_split

FEATURES_CSV = os.path.join("data", "processed", "features.csv")
FEATURE_COLUMNS = ["entropy", "length", "keyword_count", "special_char_ratio"]


def main():
    print("=== GateGuard Feature Separability & Leakage Diagnostic ===")

    if not os.path.exists(FEATURES_CSV):
        print(f"Error: {FEATURES_CSV} not found.")
        return

    df = pd.read_csv(FEATURES_CSV)
    print(f"[*] Total dataset size: {len(df)} rows.")

    benign_df = df[df["label"] == 0]
    malicious_df = df[df["label"] == 1]

    print(f"[*] Benign count (label 0): {len(benign_df)}")
    print(f"[*] Malicious count (label 1): {len(malicious_df)}")

    # 1. Feature Summary Statistics
    print("\n================ 1. FEATURE SUMMARY STATISTICS ================")
    for col in FEATURE_COLUMNS:
        b_min, b_max, b_mean = benign_df[col].min(), benign_df[col].max(), benign_df[col].mean()
        m_min, m_max, m_mean = malicious_df[col].min(), malicious_df[col].max(), malicious_df[col].mean()

        print(f"\nFeature: {col.upper()}")
        print(f"  Benign (0)   -> Min: {b_min:.4f} | Max: {b_max:.4f} | Mean: {b_mean:.4f}")
        print(f"  Malicious (1)-> Min: {m_min:.4f} | Max: {m_max:.4f} | Mean: {m_mean:.4f}")

    # 2. Train/Test Group Leakage Verification
    print("\n================ 2. GROUP-BASED LEAKAGE VERIFICATION ================")
    train_df, test_df = perform_stratified_group_chronological_split(df, train_ratio=0.8)

    train_groups = set(train_df["base_sample_id"])
    test_groups = set(test_df["base_sample_id"])
    overlap_groups = train_groups.intersection(test_groups)

    print(f"[*] Train base_sample_ids: {len(train_groups)}")
    print(f"[*] Test base_sample_ids : {len(test_groups)}")
    print(f"[*] Overlapping base_sample_ids between train and test: {len(overlap_groups)}")

    if len(overlap_groups) == 0:
        print("[SUCCESS] Zero base_sample_id leakage between train and test splits!")
    else:
        print(f"[ATTENTION] Leakage detected for: {overlap_groups}")
    print("=========================================================================")


if __name__ == "__main__":
    main()
