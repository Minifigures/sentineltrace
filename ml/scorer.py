"""Abuse scorer: a calibrated gradient-boosted model that attaches an ml_score, a SHAP
explanation, and a conformal confidence set to each alert window.

The ml_score is reported ALONGSIDE the detector's authoritative rule_score, never fused into
it: severity stays a pure function of rule_score (reproducible with no model), while ml_score
+ SHAP + conformal are decision support. SHAP explains the raw model; isotonic calibration maps
the raw score to a trustworthy probability; split-conformal yields a distribution-free set,
and an ambiguous set ({0,1}) routes the alert to mandatory human review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import shap
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split

from ml.dataset import FEATURES, build_dataset


@dataclass
class FeatureContribution:
    feature_name: str
    feature_value: float
    shap_value: float
    rank: int
    direction: str


def _shap_row(explainer, vec: np.ndarray) -> np.ndarray:
    """Positive-class SHAP row, robust across shap versions (list vs ndarray output)."""
    sv = explainer.shap_values(vec)
    if isinstance(sv, list):
        return np.asarray(sv[-1])[0]
    arr = np.asarray(sv)
    if arr.ndim == 3:
        return arr[0, :, -1]
    if arr.ndim == 2:
        return arr[0]
    return np.ravel(arr)


class AbuseScorer:
    def __init__(self, model, calibrator, explainer, base_value, qhat, feature_names):
        self.model = model
        self.calibrator = calibrator
        self.explainer = explainer
        self.base_value = base_value
        self.qhat = qhat
        self.feature_names = feature_names

    def score(self, x: dict, top_k: int = 5) -> dict:
        vec = np.array([[float(x[f]) for f in self.feature_names]])
        raw = float(self.model.predict_proba(vec)[0, 1])
        ml_score = float(np.clip(self.calibrator.predict([raw])[0], 0.0, 1.0))

        row = _shap_row(self.explainer, vec)
        order = np.argsort(np.abs(row))[::-1][:top_k]
        shap_top = [
            asdict(FeatureContribution(
                feature_name=self.feature_names[i],
                feature_value=float(x[self.feature_names[i]]),
                shap_value=float(row[i]),
                rank=rank + 1,
                direction="increases" if row[i] >= 0 else "decreases",
            ))
            for rank, i in enumerate(order)
        ]

        # split-conformal prediction set: class c is included if p(c) >= 1 - qhat
        p1, p0 = ml_score, 1.0 - ml_score
        cset = [c for c, p in ((0, p0), (1, p1)) if p >= 1.0 - self.qhat]
        return {
            "ml_score": ml_score,
            "shap_base_value": float(self.base_value),
            "shap_top_features": shap_top,
            "conformal_set": cset,
            "needs_human": cset == [0, 1] or cset == [],
        }


def train_scorer(seed: int = 0, alpha: float = 0.1) -> AbuseScorer:
    X, y, _ = build_dataset(seed=seed)
    Xtr, Xcal, ytr, ycal = train_test_split(X, y, test_size=0.3, stratify=y, random_state=seed)

    # upweight the rare positive class
    pos, neg = max(1, int((ytr == 1).sum())), max(1, int((ytr == 0).sum()))
    w = np.where(ytr == 1, neg / pos, 1.0)
    model = GradientBoostingClassifier(random_state=seed)
    model.fit(Xtr.to_numpy(), ytr, sample_weight=w)  # numpy fit -> consistent with numpy scoring

    # isotonic calibration: raw model prob -> trustworthy probability
    raw_cal = model.predict_proba(Xcal.to_numpy())[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip").fit(raw_cal, ycal)

    # conformal qhat from calibrated nonconformity on the calibration set
    cal_probs = np.clip(calibrator.predict(raw_cal), 0.0, 1.0)
    p_true = np.where(ycal == 1, cal_probs, 1.0 - cal_probs)
    nonconformity = 1.0 - p_true
    n = len(nonconformity)
    q_level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    qhat = float(np.quantile(nonconformity, q_level, method="higher"))

    explainer = shap.TreeExplainer(model)
    bv = explainer.expected_value
    base_value = float(bv[-1]) if hasattr(bv, "__len__") else float(bv)

    return AbuseScorer(model, calibrator, explainer, base_value, qhat, list(FEATURES))
