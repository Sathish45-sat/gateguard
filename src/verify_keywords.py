import os
import pandas as pd
from features import extract_features

PROCESSED_CSV = os.path.join("data", "processed", "malicious_obfuscated.csv")


def main():
    print("=== GateGuard Keyword Matching Verification ===")

    if not os.path.exists(PROCESSED_CSV):
        print(f"Error: {PROCESSED_CSV} not found.")
        return

    df = pd.read_csv(PROCESSED_CSV)

    # Filter to double_encoding or sql_comment_injection
    filtered_df = df[df["technique"].isin(["double_encoding", "sql_comment_injection"])].copy()

    print(f"[*] Found {len(filtered_df)} total obfuscated samples matching filter.")

    zero_count_samples = []

    print("\n--- Testing All Obfuscated Filtered Strings ---")
    for idx, row in filtered_df.iterrows():
        req_str = row["request_string"]
        tech = row["technique"]
        feats = extract_features(req_str)
        kw_count = feats["keyword_count"]

        print(f"[{tech:21s}] '{req_str}' -> keyword_count: {kw_count}")

        if kw_count == 0:
            zero_count_samples.append((tech, req_str))

    print("\n================ VERIFICATION RESULT ================")
    if not zero_count_samples:
        print("[SUCCESS] All obfuscated samples produced keyword_count > 0!")
    else:
        print(f"[ATTENTION] {len(zero_count_samples)} obfuscated sample(s) produced keyword_count == 0:")
        for tech, req_str in zero_count_samples:
            print(f"  - [{tech}] '{req_str}'")
    print("=====================================================")


if __name__ == "__main__":
    main()
