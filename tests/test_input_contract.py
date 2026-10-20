"""Negative-path, scientific-safety and deterministic property regression tests."""
from __future__ import annotations

import dataclasses
import json
import math
import random

import pytest

from mindbench.alignment import align_trials, quality_summary
from mindbench.benchmark import benchmark, subject_split
from mindbench.cohort import Example, synthetic_cohort
from mindbench.io import read_json
from mindbench.schema import ClockContract, ResourceLimits, Rights, ValidationError


def real_rights(**changes: object) -> Rights:
    values = dict(license="CC0-1.0", source_url="https://example.org/dataset",
                  dataset_id="test", dataset_version="1", citation="synthetic test",
                  attested_by="automated test", synthetic=False)
    values.update(changes)
    return Rights(**values)


@pytest.mark.parametrize("field,value", [
    ("synthetic", "false"),
    ("synthetic", 0),
    ("license", ["CC0-1.0"]),
    ("source_url", "https://"),
    ("source_url", "https:///invalid"),
    ("source_url", "https://example.org/\nsource"),
    ("source_url", 5),
    ("citation", " "),
])
def test_rejects_malformed_rights(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        real_rights(**{field: value})


@pytest.mark.parametrize("changes", [
    {"hardware_synced": "false"},
    {"hardware_synced": 0},
    {"behavior_origin": "relative_to_stimulus"},
    {"eeg_origin": "wallclock"},
])
def test_rejects_invalid_clock_claims(changes: dict) -> None:
    with pytest.raises(ValidationError):
        ClockContract(**changes)


@pytest.mark.parametrize("changes", [
    {"max_events": True}, {"max_channels": 4.2}, {"max_samples": -10},
])
def test_rejects_unbounded_or_mistyped_limits(changes: dict) -> None:
    with pytest.raises(ValidationError):
        ResourceLimits(**changes)


@pytest.mark.parametrize("value", [
    '{"license": "CC0-1.0", "license": "synthetic"}',
    '{"origin": NaN}',
    '{"origin": Infinity}',
    '[1, 2]',
])
def test_rejects_invalid_json_metadata(tmp_path, value: str) -> None:
    path = tmp_path / "metadata.json"
    path.write_text(value)
    with pytest.raises(ValidationError):
        read_json(path)


@pytest.mark.parametrize("changed,needle", [
    ({"eeg": (float("nan"), 1.)}, "finite"),
    ({"behavior": (float("inf"), 1.)}, "finite"),
    ({"eeg": (1.,)}, "two features"),
    ({"eeg": (1., "not-number")}, "finite"),
    ({"behavior": (True, 1.)}, "finite"),
    ({"label": True}, "binary integer"),
    ({"label": 3}, "binary integer"),
    ({"subject": ""}, "identity"),
    ({"session": " "}, "identity"),
    ({"sample_id": ""}, "identity"),
])
def test_model_input_validation_rejects_corrupt_features(changed: dict, needle: str) -> None:
    rows = synthetic_cohort(n_subjects=12, trials_per_subject=8, seed=41)
    rows[0] = dataclasses.replace(rows[0], **changed)
    with pytest.raises(ValidationError, match=needle):
        subject_split(rows)
    with pytest.raises(ValidationError, match=needle):
        benchmark(rows, reps=10)


def test_model_accepts_numeric_list_features() -> None:
    rows = synthetic_cohort(n_subjects=12, trials_per_subject=10, seed=49)
    rows = [dataclasses.replace(r, eeg=list(r.eeg) if r.eeg is not None else None,
                                behavior=list(r.behavior) if r.behavior is not None else None)
            for r in rows]
    result = benchmark(rows, reps=10)
    assert result["results"]["early_fusion"]["n"] > 0


def test_missing_modalities_never_count_as_valid_and_reconcile() -> None:
    # Missing EEG AND behavioral response cannot be an analysis-valid trial.
    trials = align_trials([{"onset": 1.0, "trial_type": "stimulus"}], None,
                          ClockContract(), eeg_duration_s=None)
    qc = quality_summary(trials)
    assert not trials[0].valid
    assert qc["n_valid"] == 0
    assert qc["neither_modality"] == 1
    assert qc["complete_modalities"] == 0

    ev = [{"onset": 1. + i * 1.5, "trial_type": str(i)} for i in range(3)]
    re = [{"onset": 1.2, "response": "a"}, {"onset": 4.2, "response": "b"}]
    trials = align_trials(ev, re, ClockContract(behavior_origin="acquisition_start"), eeg_duration_s=3.0)
    qc = quality_summary(trials)
    assert sum(qc[key] for key in ("complete_modalities", "eeg_only", "behavior_only", "neither_modality")) == qc["n_trials"]
    assert qc["complete_modalities"] <= qc["with_eeg"]
    assert qc["complete_modalities"] <= qc["with_behavior"]


def test_randomized_alignment_no_reused_response_or_future_event_assignment() -> None:
    rng = random.Random(105)
    for _ in range(75):
        times = sorted(rng.sample(range(1, 10000), k=45))
        events = [{"onset": t / 100., "trial_type": "t"} for t in times]
        responses = [{"onset": t / 100., "response": f"r{i}"}
                     for i, t in enumerate(sorted(rng.sample(range(1, 10000), k=65)))]
        trials = align_trials(events, responses, ClockContract(behavior_origin="acquisition_start"),
                              eeg_duration_s=150.0, max_latency_s=0.75)
        observed = [trial.response for trial in trials if trial.response is not None]
        assert len(observed) == len(set(observed))
        for i, trial in enumerate(trials):
            if trial.response_s is not None:
                assert trial.onset_s <= trial.response_s
                assert trial.latency_s is not None and trial.latency_s <= .75
                if i < len(trials) - 1:
                    assert trial.response_s < trials[i + 1].onset_s


def test_no_mislabeling_of_unknown_data_as_synthetic() -> None:
    rows = synthetic_cohort(n_subjects=12, trials_per_subject=10)
    default = benchmark(rows, reps=10)
    assert default["data_kind"] == "unverified_feature_vectors"
    assert default["audit"]["label_origin"] == "unverified"
    asserted = benchmark(rows, reps=10, source_kind="synthetic")
    assert asserted["data_kind"] == "fully_synthetic_simulated_features"
    assert asserted["audit"]["label_origin"] == "synthetic_programmatic"
    with pytest.raises(ValidationError, match="source kind"):
        benchmark(rows, reps=10, source_kind="unlicensed")
