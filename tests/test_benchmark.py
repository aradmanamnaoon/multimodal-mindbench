from copy import copy
import pytest
from mindbench.benchmark import benchmark, subject_split, _metric_bundle
from mindbench.cohort import Example, synthetic_cohort
from mindbench.schema import ValidationError


def test_grouping_no_leakage_and_determinism():
    rows = synthetic_cohort(n_subjects=16, trials_per_subject=12, seed=5)
    a = subject_split(rows, seed=7)
    assert all(not a[x].intersection(a[y]) for x, y in (("train", "test"), ("test", "calibration"), ("calibration", "train")))
    assert a == subject_split(rows, seed=7)
    result = benchmark(rows, seed=7, reps=50)
    assert result == benchmark(rows, seed=7, reps=50)
    assert result["audit"]["subject_leakage"] is False
    assert result["sample_counts"]["test"] >= result["sample_counts"]["common_complete_test"]
    assert set(result["results"]) == {"behavior", "eeg", "early_fusion", "late_fusion", "late_fusion_available_modality"}
    for name in ("behavior", "eeg", "early_fusion", "late_fusion"):
        m = result["results"][name]
        assert m["scope"] == "complete_cases"
        assert m["n"] == result["sample_counts"]["common_complete_test"]
        assert 0 <= m["roc_auc"] <= 1 and 0 <= m["ece10"] <= 1


def test_missing_modality_fallback():
    rows = synthetic_cohort(n_subjects=16, trials_per_subject=20, missing_rate=.35)
    result = benchmark(rows, reps=30)
    assert result["results"]["late_fusion_available_modality"]["n"] >= result["results"]["late_fusion"]["n"]


def test_bad_cohort_and_sample_id():
    with pytest.raises(ValidationError):
        synthetic_cohort(n_subjects=3)
    rows = synthetic_cohort(n_subjects=10, trials_per_subject=10)
    with pytest.raises(ValidationError, match="Duplicate"):
        subject_split(rows + [rows[0]])
    with pytest.raises(ValidationError):
        benchmark([Example("a", "s", "01", 1, (1., 2.), (2., 3.))])
    with pytest.raises(ValidationError):
        _metric_bundle(rows[:2], [0.3, float("nan")])
