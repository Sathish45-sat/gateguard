import os
import joblib
import numpy as np
import pandas as pd
import onnxruntime as rt

from onnxmltools import convert_xgboost
from onnxmltools.convert.common.data_types import FloatTensorType
from xgboost import XGBClassifier

from train import FEATURE_COLUMNS, TARGET_COLUMN, perform_stratified_group_chronological_split

FEATURES_CSV = os.path.join("data", "processed", "features.csv")
MODEL_PATH = os.path.join("models", "gateguard_model.pkl")
ONNX_PATH = os.path.join("models", "gateguard_model.onnx")


def export_model_to_onnx(model: XGBClassifier):
    """
    Convert XGBClassifier model to ONNX format with a single float32 input tensor
    named 'input' of shape [None, 4].
    """
    # Fix booster feature names to f0, f1, f2, f3 for ONNX tree attribute parser compatibility
    booster = model.get_booster()
    booster.feature_names = [f"f{i}" for i in range(len(FEATURE_COLUMNS))]

    initial_types = [("input", FloatTensorType([None, 4]))]

    onnx_model = convert_xgboost(
        model,
        initial_types=initial_types,
        target_opset=12,
    )

    os.makedirs("models", exist_ok=True)
    with open(ONNX_PATH, "wb") as f:
        f.write(onnx_model.SerializeToString())

    print(f"[+] Saved ONNX model artifact to {ONNX_PATH}")
    return ONNX_PATH


def validate_onnx_export(model: XGBClassifier, test_df: pd.DataFrame):
    """
    Take 10 random sample rows from test set, run inference on both XGBoost and ONNX,
    and print a side-by-side comparison table of predictions and probabilities.
    """
    print("\n--- Validating ONNX Export vs XGBoost Model (10 Sample Rows) ---")

    # Select 10 sample rows
    sample_df = test_df.sample(min(10, len(test_df)), random_state=42).reset_index(drop=True)
    X_samples = sample_df[FEATURE_COLUMNS].values.astype(np.float32)
    y_true = sample_df[TARGET_COLUMN].values

    # 1. XGBoost Inference
    xgb_preds = model.predict(X_samples)
    xgb_probs = model.predict_proba(X_samples)[:, 1]  # Malicious class probability

    # 2. ONNX Runtime Inference
    sess = rt.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[0].name
    proba_name = sess.get_outputs()[1].name

    onnx_res = sess.run([label_name, proba_name], {input_name: X_samples})
    onnx_preds = onnx_res[0]
    onnx_probs_raw = onnx_res[1]

    # Extract class 1 probability from ONNX output
    if isinstance(onnx_probs_raw, list):
        # List of dicts if zipmap was enabled
        onnx_probs = np.array([p[1] for p in onnx_probs_raw], dtype=np.float32)
    elif isinstance(onnx_probs_raw, np.ndarray):
        if onnx_probs_raw.ndim == 2 and onnx_probs_raw.shape[1] == 2:
            onnx_probs = onnx_probs_raw[:, 1]
        else:
            onnx_probs = onnx_probs_raw.ravel()

    # 3. Print Comparison Table
    print(f"{'Row':<4} | {'True Label':<10} | {'XGB Pred (Prob)':<20} | {'ONNX Pred (Prob)':<20} | {'Match?':<8}")
    print("-" * 75)

    all_matched = True
    failed_rows = []

    for i in range(len(sample_df)):
        t_label = y_true[i]
        x_pred, x_prob = xgb_preds[i], xgb_probs[i]
        o_pred, o_prob = onnx_preds[i], onnx_probs[i]

        pred_match = (x_pred == o_pred)
        prob_close = np.isclose(x_prob, o_prob, atol=1e-4)
        matched = pred_match and prob_close

        if not matched:
            all_matched = False
            failed_rows.append((i+1, x_pred, o_pred, abs(x_prob - o_prob)))

        status = "PASS" if matched else "FAIL"
        print(f"{i+1:<4} | {t_label:<10} | {x_pred} ({x_prob:.6f})        | {o_pred} ({o_prob:.6f})        | {status:<8}")

    print("\n================ ONNX VALIDATION SUMMARY ================")
    if all_matched:
        print("[SUCCESS] All 10 test samples match perfectly between XGBoost and ONNX runtime!")
    else:
        print(f"[FAIL] {len(failed_rows)} mismatch(es) detected between XGBoost and ONNX runtime predictions:")
        for r_num, x_p, o_p, p_diff in failed_rows:
            print(f"  - Row {r_num}: XGB Pred={x_p}, ONNX Pred={o_p}, Prob Diff={p_diff:.6f}")
    print("=========================================================")


def main():
    print("=== GateGuard Model ONNX Export & Validation Pipeline ===")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    print(f"[*] Loaded trained model from {MODEL_PATH}")

    # 1. Export model to ONNX
    export_model_to_onnx(model)

    # 2. Load test set for validation
    df = pd.read_csv(FEATURES_CSV)
    _, test_df = perform_stratified_group_chronological_split(df, train_ratio=0.8)

    # 3. Validate export
    validate_onnx_export(model, test_df)


if __name__ == "__main__":
    main()
