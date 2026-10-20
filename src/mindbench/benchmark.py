"""Nonclinical, group-disjoint benchmarks on simulated features only.

No participant data or medical prediction task is included. The outer test
subjects never influence training, calibration, scaling or feature selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import numbers
import random
from typing import Any, Iterable, Literal, Sequence

from .cohort import Example
from .schema import ValidationError

MetricScope = Literal["complete_cases", "available_modalities"]


def _deps():
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import roc_auc_score, brier_score_loss
    except ImportError as exc:
        raise ValidationError("Research benchmarking requires mindbench[benchmark] on a hosted runner") from exc
    return np, LogisticRegression, make_pipeline, StandardScaler, roc_auc_score, brier_score_loss


def validate_examples(rows: Sequence[Example]) -> None:
    """Reject invalid identities, non-binary targets, and unsafe model features.

    Validation precedes splitting and model fitting so scientific input problems
    do not surface as misleading scikit-learn errors or silently coerce NaNs.
    """
    for index, row in enumerate(rows):
        if not isinstance(row, Example):
            raise ValidationError(f"Example {index}: expected a cohort Example")
        if any(not isinstance(value, str) or not value.strip()
               for value in (row.sample_id, row.subject, row.session)):
            raise ValidationError(f"Example {index}: missing sample/subject/session identity")
        if type(row.label) is not int or row.label not in (0, 1):
            raise ValidationError(f"Example {index}: binary integer label 0 or 1 required")
        for modality in ("eeg", "behavior"):
            features = getattr(row, modality)
            if features is None:
                continue
            if not isinstance(features, (list, tuple)) or len(features) != 2:
                raise ValidationError(f"Example {index}: {modality} needs two features")
            if any(isinstance(v, bool) or not isinstance(v, numbers.Real) or not math.isfinite(v)
                   for v in features):
                raise ValidationError(f"Example {index}: {modality} features must be finite real numbers")


def subject_split(rows: Sequence[Example], *, seed: int = 2026,
                  test_fraction: float = 0.25, calibration_fraction: float = .25) -> dict[str, set[str]]:
    """Three disjoint subject sets, with no duplicated sample identifier."""
    if not 0.10 <= test_fraction <= .4 or not .15 <= calibration_fraction <= .4:
        raise ValidationError("Invalid subject split fractions")
    validate_examples(rows)
    groups = sorted({r.subject for r in rows})
    if len(groups) < 8 or len(rows) < 16:
        raise ValidationError("At least 8 independent subjects and 16 rows required")
    sample_ids = [r.sample_id for r in rows]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValidationError("Duplicate sample identifiers")
    rng = random.Random(seed)
    rng.shuffle(groups)
    n_test = max(2, int(round(len(groups) * test_fraction)))
    other = groups[n_test:]
    n_cal = max(2, int(round(len(other) * calibration_fraction)))
    result = {"test": set(groups[:n_test]), "calibration": set(other[:n_cal]),
              "train": set(other[n_cal:])}
    if min(map(len, result.values())) < 2:
        raise ValidationError("Too few subjects in train/calibration/test")
    for key, subject_ids in result.items():
        subset_labels = {r.label for r in rows if r.subject in subject_ids and r.eeg is not None and r.behavior is not None}
        if subset_labels != {0, 1}:
            raise ValidationError(f"Complete-case split {key} does not contain two classes")
    if result["train"] & result["test"] or result["train"] & result["calibration"] or result["test"] & result["calibration"]:
        raise ValidationError("Subject leakage across splits")
    return result


def _complete(row: Example) -> bool:
    return row.eeg is not None and row.behavior is not None


def _features(row: Example, modality: str) -> list[float] | None:
    if modality == "eeg":
        return list(row.eeg) if row.eeg is not None else None
    if modality == "behavior":
        return list(row.behavior) if row.behavior is not None else None
    if modality == "early_fusion":
        return list(row.eeg) + list(row.behavior) if _complete(row) else None
    raise ValidationError(f"Unsupported modality: {modality}")


def _fit_calibrated(train: list[Example], calibration: list[Example], modality: str, seed: int):
    np, LR, make_pipeline, scaler, _, _ = _deps()
    tr = [r for r in train if _features(r, modality) is not None]
    ca = [r for r in calibration if _features(r, modality) is not None]
    if {r.label for r in tr} != {0, 1} or {r.label for r in ca} != {0, 1}:
        raise ValidationError("Insufficient per-modality training/calibration classes")
    model = make_pipeline(scaler(), LR(max_iter=500, solver="liblinear", random_state=seed))
    model.fit(np.asarray([_features(r, modality) for r in tr], dtype=float), [r.label for r in tr])
    # Learn a sigmoid only from held-out calibration subjects. No row-level CV.
    raw = model.predict_proba(np.asarray([_features(r, modality) for r in ca], dtype=float))[:, 1]
    logit = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / np.clip(1 - raw, 1e-6, 1))
    calibrator = LR(solver="liblinear", random_state=seed, max_iter=500)
    calibrator.fit(logit.reshape(-1, 1), [r.label for r in ca])
    return model, calibrator, len(tr), len(ca)


def _predict(model_pair, row: Example, modality: str) -> float | None:
    features = _features(row, modality)
    if features is None:
        return None
    model, calibrator, _, _ = model_pair
    np, *_ = _deps()
    prob = float(model.predict_proba(np.asarray([features], dtype=float))[0, 1])
    prob = min(max(prob, 1e-6), 1 - 1e-6)
    logit = math.log(prob / (1 - prob))
    return float(calibrator.predict_proba(np.asarray([[logit]]))[0, 1])


def _metric_bundle(rows: Sequence[Example], probabilities: Sequence[float]) -> dict[str, float | int | None]:
    np, _, _, _, roc_auc_score, brier_score_loss = _deps()
    y = [r.label for r in rows]
    if not y or len(y) != len(probabilities) or any(not math.isfinite(float(p)) or not 0 <= p <= 1 for p in probabilities):
        raise ValidationError("Invalid metric inputs")
    predicted = [int(p >= .5) for p in probabilities]
    acc = sum(a == b for a, b in zip(y, predicted)) / len(y)
    recalls = [sum(predicted[i] == label for i in range(len(y)) if y[i] == label) / sum(x == label for x in y)
               for label in (0, 1) if label in y]
    ece = 0.0
    for left in range(10):
        indices = [i for i, p in enumerate(probabilities) if (left / 10 <= p < (left + 1) / 10) or (left == 9 and p == 1)]
        if indices:
            conf = sum(probabilities[i] for i in indices) / len(indices)
            freq = sum(y[i] for i in indices) / len(indices)
            ece += abs(conf - freq) * len(indices) / len(y)
    return {"n": len(y), "accuracy": round(acc, 6),
            "balanced_accuracy": round(sum(recalls) / len(recalls), 6),
            "roc_auc": round(float(roc_auc_score(y, probabilities)), 6) if len(set(y)) == 2 else None,
            "brier": round(float(brier_score_loss(y, probabilities)), 6),
            "ece10": round(ece, 6)}


def _cluster_accuracy_interval(rows: Sequence[Example], probs: Sequence[float], *, seed: int, reps: int = 300) -> list[float]:
    """Subject cluster bootstrap of accuracy (test set only; descriptive CI)."""
    if reps < 10:
        raise ValidationError("Bootstrap requires at least 10 resamples")
    groups = sorted({r.subject for r in rows})
    rng = random.Random(seed)
    by_subject = {s: [i for i, r in enumerate(rows) if r.subject == s] for s in groups}
    stats: list[float] = []
    for _ in range(reps):
        selected = [i for _ in groups for i in by_subject[rng.choice(groups)]]
        stats.append(sum(int(probs[i] >= 0.5) == rows[i].label for i in selected) / len(selected))
    stats.sort()
    return [round(stats[int(.025 * (reps - 1))], 6), round(stats[int(.975 * (reps - 1))], 6)]


def benchmark(rows: Sequence[Example], *, seed: int = 2026, reps: int = 300,
              source_kind: Literal["unverified", "synthetic"] = "unverified") -> dict[str, Any]:
    """Four registered candidates, common holdout for fair complete-case comparison.

    Late fusion falls back to a unimodal prediction when an input is missing;
    missingness robustness is separately quantified on the *whole* test fold.
    """
    if source_kind not in ("unverified", "synthetic"):
        raise ValidationError("Benchmark source kind must be explicitly unverified or synthetic")
    validate_examples(rows)
    if not rows or {r.label for r in rows} != {0, 1}:
        raise ValidationError("Binary nonempty class labels 0 and 1 required")
    partitions = subject_split(rows, seed=seed)
    tr = [r for r in rows if r.subject in partitions["train"]]
    ca = [r for r in rows if r.subject in partitions["calibration"]]
    te = [r for r in rows if r.subject in partitions["test"]]
    models = {name: _fit_calibrated(tr, ca, name, seed) for name in ("eeg", "behavior", "early_fusion")}
    te_common = [r for r in te if _complete(r)]
    if {r.label for r in te_common} != {0, 1}:
        raise ValidationError("Both classes required in common test set")
    outcomes: dict[str, Any] = {}
    predictions: dict[str, list[float]] = {}
    for key in ("eeg", "behavior", "early_fusion", "late_fusion"):
        if key == "late_fusion":
            probs = [(_predict(models["eeg"], r, "eeg") + _predict(models["behavior"], r, "behavior")) / 2 for r in te_common]
        else:
            probs = [_predict(models[key], r, key) for r in te_common]
        assert all(p is not None for p in probs)
        predictions[key] = probs
        outcomes[key] = _metric_bundle(te_common, probs)
        outcomes[key]["accuracy_subject_bootstrap_95pct"] = _cluster_accuracy_interval(te_common, probs, seed=seed + len(key), reps=reps)
        outcomes[key]["scope"] = "complete_cases"
    robustness_rows: list[Example] = []
    robustness_probs: list[float] = []
    for r in te:
        left = _predict(models["eeg"], r, "eeg")
        right = _predict(models["behavior"], r, "behavior")
        if left is None and right is None:
            continue
        robustness_rows.append(r)
        robustness_probs.append((left + right) / 2 if left is not None and right is not None else (left if left is not None else right))
    outcomes["late_fusion_available_modality"] = _metric_bundle(robustness_rows, robustness_probs)
    outcomes["late_fusion_available_modality"]["scope"] = "available_modalities"
    return {
        "schema": "mindbench-benchmark-v1",
        "data_kind": "fully_synthetic_simulated_features" if source_kind == "synthetic" else "unverified_feature_vectors",
        "purpose": "Software-method validation ONLY; no independently validated empirical findings",
        "seed": seed, "bootstrap_repetitions": reps,
        "cohort_digest_sha256": hashlib.sha256(json.dumps([r.to_dict() for r in rows], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "subjects": {s: sorted(v) for s, v in partitions.items()},
        "sample_counts": {"train": len(tr), "calibration": len(ca), "test": len(te), "common_complete_test": len(te_common)},
        "fit_sizes": {k: {"train": m[2], "calibration": m[3]} for k, m in models.items()},
        "results": outcomes,
        "audit": {"subject_leakage": False, "threshold": .5, "threshold_selected_on_test": False,
                  "calibration_subject_disjoint": True, "preprocessing_fit_on_train_only": True,
                  "label_origin": "synthetic_programmatic" if source_kind == "synthetic" else "unverified", "external_validation": False},
        "limitations": [
            ("Synthetic feature values are not EEG waveforms, measured reaction times or clinical outcomes."
             if source_kind == "synthetic" else
             "Feature origin, consent, license and event-clock validity are not verified by this benchmark API."),
            "Accuracy intervals are subject-cluster bootstraps conditional on one synthetic held-out split, not population CIs.",
            "Calibration is fit solely on reserved calibration subjects; ECE10 is descriptive and sensitive to binning.",
            "Complete-case comparison excludes samples with missing modalities, potentially selecting a biased subset.",
            "Late fusion missing-input robustness uses a different test denominator and is not directly comparable.",
            "No claim of hardware synchronization, fairness, generalizability to people or diagnostic performance.",
        ],
    }
