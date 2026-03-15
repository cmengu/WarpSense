"""
Weld quality classifier: LOF/LOP-focused, trained on SessionFeatures.

Uses the 11 features from session_feature_extractor. Predicts quality_class
(GOOD | MARGINAL | DEFECTIVE) with confidence and per-class probabilities.

Caller must run from backend/ or have backend/ on PYTHONPATH.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from features.session_feature_extractor import SessionFeatures

# Feature order must match SessionFeatures.to_vector() keys.
# Used for X matrix construction and importance mapping.
FEATURE_COLS = [
    "heat_input_mean",
    "heat_input_min_rolling",
    "heat_input_drop_severity",
    "heat_input_cv",
    "angle_deviation_mean",
    "angle_max_drift_1s",
    "voltage_cv",
    "amps_cv",
    "heat_diss_mean",
    "heat_diss_max_spike",
    "arc_on_ratio",
]


@dataclass
class WeldPrediction:
    """Prediction for a single session."""

    session_id: str
    quality_class: str  # GOOD | MARGINAL | DEFECTIVE
    confidence: float  # 0.0 to 1.0, max class probability
    all_probabilities: Dict[str, float]  # class name -> probability
    top_drivers: list = field(default_factory=list)  # List[Tuple[str, float]] — (feature_name, importance), top 3


def _features_to_array(features: SessionFeatures) -> np.ndarray:
    """Convert SessionFeatures to row vector in FEATURE_COLS order."""
    vec = features.to_vector()
    return np.array([float(vec[c]) for c in FEATURE_COLS], dtype=np.float64)


class WeldClassifier:
    """
    Trains on SessionFeatures and predicts quality_class.
    Uses GradientBoostingClassifier (sklearn) — no XGBoost dependency.
    """

    def __init__(self):
        self._model = None  # GradientBoostingClassifier after train()
        self._classes: List[str] = []

    def train(self, dataset: List[SessionFeatures]) -> dict:
        """
        Train on labeled SessionFeatures. Returns report dict with
        train_accuracy, warning, and top_3_drivers (feature name, importance).
        """
        if not dataset:
            raise ValueError("Empty dataset — cannot train")

        X = np.array([_features_to_array(f) for f in dataset], dtype=np.float64)
        labels = [f.quality_label for f in dataset]
        if any(lbl is None for lbl in labels):
            raise ValueError("All samples must have quality_label for training")

        # Unique classes in order of first appearance (deterministic)
        self._classes = []
        for lbl in labels:
            if lbl not in self._classes:
                self._classes.append(lbl)

        y = np.array([self._classes.index(lbl) for lbl in labels], dtype=np.int64)

        self._model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        self._model.fit(X, y)

        # Train accuracy
        y_pred = self._model.predict(X)
        train_accuracy = float(np.mean(y_pred == y))

        # Warnings for small/imbalanced data
        warning = ""
        if len(dataset) < 20:
            warning = f"Small training set ({len(dataset)} sessions) — consider more data"
        class_counts = {c: labels.count(c) for c in self._classes}
        min_count = min(class_counts.values())
        if min_count < 3:
            warning = (
                warning + " "
                if warning
                else ""
            ) + f"Minority class has only {min_count} samples"

        # Top 3 feature drivers by importance
        importances = self._model.feature_importances_
        ranked = sorted(
            list(zip(FEATURE_COLS, importances)),
            key=lambda p: p[1],
            reverse=True,
        )
        top_3_drivers = [(name, float(imp)) for name, imp in ranked[:3]]

        return {
            "train_accuracy": train_accuracy,
            "warning": warning.strip() if warning else None,
            "top_3_drivers": top_3_drivers,
        }

    def predict(self, features: SessionFeatures) -> WeldPrediction:
        """Predict quality class for a single SessionFeatures. Must call train() first."""
        if self._model is None:
            raise RuntimeError("Classifier not trained — call train() first")

        x = _features_to_array(features).reshape(1, -1)
        probs = self._model.predict_proba(x)[0]

        # Map indices to class names
        all_probabilities = {c: float(probs[i]) for i, c in enumerate(self._classes)}
        # Ensure DEFECTIVE exists (0 if never seen in training)
        if "DEFECTIVE" not in all_probabilities:
            all_probabilities["DEFECTIVE"] = 0.0

        pred_class_idx = int(np.argmax(probs))
        quality_class = self._classes[pred_class_idx]
        confidence = float(probs[pred_class_idx])

        importances = zip(FEATURE_COLS, self._model.feature_importances_)
        ranked = sorted(importances, key=lambda x: x[1], reverse=True)
        top_drivers = [(name, float(imp)) for name, imp in ranked[:3]]

        return WeldPrediction(
            session_id=features.session_id,
            quality_class=quality_class,
            confidence=confidence,
            all_probabilities=all_probabilities,
            top_drivers=top_drivers,
        )
