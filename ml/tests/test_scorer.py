import numpy as np

from ml.dataset import build_dataset
from ml.scorer import train_scorer


def _clear_windows(X, y):
    abuse = X[y == 1]
    benign = X[y == 0]
    clear_abuse = abuse.sort_values("cancel_ratio", ascending=False).iloc[0].to_dict()
    clear_benign = benign.sort_values("n_orders").iloc[0].to_dict()
    return clear_abuse, clear_benign


def test_scorer_separates_abuse_from_benign():
    scorer = train_scorer(seed=0)
    X, y, _ = build_dataset(seed=2)  # different seed -> out-of-sample-ish windows
    abuse, benign = _clear_windows(X, y)
    a = scorer.score(abuse)
    b = scorer.score(benign)
    assert a["ml_score"] > 0.5
    assert b["ml_score"] < 0.5
    assert a["ml_score"] > b["ml_score"]


def test_shap_top_features_have_canonical_shape():
    scorer = train_scorer(seed=0)
    X, y, _ = build_dataset(seed=2)
    abuse, _ = _clear_windows(X, y)
    out = scorer.score(abuse)
    assert len(out["shap_top_features"]) == 5
    fc = out["shap_top_features"][0]
    assert set(fc.keys()) == {"feature_name", "feature_value", "shap_value", "rank", "direction"}
    assert fc["rank"] == 1
    assert fc["direction"] in ("increases", "decreases")


def test_conformal_set_flags_clear_abuse_and_routes_ambiguous_to_human():
    scorer = train_scorer(seed=0)
    X, y, _ = build_dataset(seed=2)
    abuse, benign = _clear_windows(X, y)
    assert 1 in scorer.score(abuse)["conformal_set"]
    assert 0 in scorer.score(benign)["conformal_set"]


def test_ml_score_does_not_drive_severity_contract():
    # the scorer only produces ml_score/shap/conformal; severity stays detector-owned.
    scorer = train_scorer(seed=0)
    X, y, _ = build_dataset(seed=2)
    out = scorer.score(_clear_windows(X, y)[0])
    assert set(out.keys()) == {"ml_score", "shap_base_value", "shap_top_features", "conformal_set", "needs_human"}
    assert "severity" not in out
