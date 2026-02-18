"""
Trains warp prediction model and exports to ONNX.

skl2onnx output for Pipeline(StandardScaler, LogisticRegression):
  result = sess.run(None, {input_name: X})
  result[1][i][1] = P(class=1) = P(will_breach)

Usage:
  python -m backend.scripts.train_warp_model \\
    --input data/training_data.csv \\
    --output backend/models/warp_model.onnx
"""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
import skl2onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from features.warp_features import FEATURE_COLS

SKL2ONNX_MIN = "1.16.0"
ONNXRUNTIME_MIN = "1.17.0"


def _parse_version(v: str) -> tuple:
    """Parse '1.16.0' or '1.17.1' -> (1, 16, 0) for comparison. Handles suffixes like .dev, .post1."""
    parts = []
    for p in v.split(".")[:3]:
        num = "".join(c for c in p if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/training_data.csv")
    parser.add_argument("--output", default="backend/models/warp_model.onnx")
    args = parser.parse_args()

    if _parse_version(skl2onnx.__version__) < _parse_version(SKL2ONNX_MIN):
        raise RuntimeError(
            f"skl2onnx >= {SKL2ONNX_MIN} required; got {skl2onnx.__version__}"
        )
    import onnxruntime as ort

    if _parse_version(ort.__version__) < _parse_version(ONNXRUNTIME_MIN):
        raise RuntimeError(
            f"onnxruntime >= {ONNXRUNTIME_MIN} required; got {ort.__version__}"
        )
    assert np.__version__.startswith(
        "1."
    ), f"numpy must be 1.x for sklearn/onnxruntime float32 consistency; got {np.__version__}"

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    with open(input_path) as f:
        rows = list(csv.DictReader(f))

    if len(rows) == 0:
        raise ValueError("Training CSV is empty")

    y = np.array([int(r["will_breach"]) for r in rows])
    min_per_class = min(np.sum(y == 0), np.sum(y == 1))
    if min_per_class < 2:
        raise ValueError(
            f"stratify requires min 2 per class; got {int(np.sum(y==1))} pos, {int(np.sum(y==0))} neg"
        )

    csv_sha = hashlib.sha256(input_path.read_bytes()).hexdigest()[:16]
    print(f"Training from {input_path} (sha256 prefix: {csv_sha})")

    X = np.array([[float(r[c]) for c in FEATURE_COLS] for r in rows], dtype=np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=500)),
        ]
    )
    pipeline.fit(X_train, y_train)

    if len(X_test) > 0:
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        print(f"Test AUC: {auc:.4f}")
        if auc < 0.70:
            print("WARNING: AUC below 0.70 — check training data quality")
    else:
        print("WARNING: X_test empty (tiny dataset) — skipping AUC")

    initial_type = [("float_input", FloatTensorType([None, len(FEATURE_COLS)]))]
    onnx_model = convert_sklearn(pipeline, initial_types=initial_type)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Exported to {out_path}")

    prov_path = out_path.with_suffix(".onnx.provenance.txt")
    prov_path.write_text(
        f"input_csv={input_path.resolve()}\ncsv_sha256_prefix={csv_sha}\n"
    )

    sess = ort.InferenceSession(str(out_path))
    input_name = sess.get_inputs()[0].name
    X_verify = (
        X_test[:10] if len(X_test) >= 1 else X_train[: min(10, len(X_train))]
    )
    if len(X_verify) == 0:
        raise ValueError("No samples for ONNX verification — dataset too small")
    sklearn_probs = pipeline.predict_proba(X_verify)[:, 1]
    result = sess.run(None, {input_name: X_verify})
    onnx_probs = result[1][:, 1]
    max_diff = float(np.max(np.abs(sklearn_probs - onnx_probs)))
    if max_diff > 1e-5:
        raise AssertionError(
            f"ONNX output differs from sklearn: max diff = {max_diff}"
        )
    print(f"ONNX vs sklearn match: max diff = {max_diff:.2e}")

    assert out_path.stat().st_size > 1024


if __name__ == "__main__":
    main()
