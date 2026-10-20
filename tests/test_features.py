import pytest
from mindbench.alignment import align_trials
from mindbench.features import run_features, window_means
from mindbench.schema import ClockContract, SubjectSession, ValidationError
from mindbench.synthetic import generate_fixture


def test_audit_to_features_end_to_end(tmp_path):
    root = generate_fixture(tmp_path / "fixture")
    ident = SubjectSession("01", "01", "oddball", "01")
    rows, audit = run_features(root, ident, {"standard": 0, "deviant": 1})
    assert len(rows) == 3
    assert len(rows[0].eeg) == 2
    assert rows[0].behavior[0] == pytest.approx(.2)
    assert {r.label for r in rows} == {0, 1}
    assert audit["rights_independently_verified"] is False
    with pytest.raises(ValidationError, match="map explicitly"):
        run_features(root, ident, {"standard": 0})


def test_unverified_clock_excludes_behavior(tmp_path):
    root = generate_fixture(tmp_path / "fixture")
    (root / "clock.json").write_text('{"behavior_origin":"unverified"}')
    rows, _ = run_features(root, SubjectSession("01", "01", "oddball", "01"), {"standard": 0, "deviant": 1})
    assert all(r.behavior is None for r in rows)
    assert all(r.eeg is not None for r in rows)


def test_missing_window_and_epoch_limits(tmp_path):
    root = generate_fixture(tmp_path / "fixture")
    ident = SubjectSession("01", "01", "oddball", "01")
    trials = align_trials([{"onset": 4., "trial_type": "a"}], None, ClockContract(), eeg_duration_s=3)
    assert window_means(root, ident, trials, {"SamplingFrequency": 100, "MindBenchAdapter": "synthetic-tsv"}) == [None]
    with pytest.raises(ValidationError):
        window_means(root, ident, trials, {"SamplingFrequency": 100, "MindBenchAdapter": "synthetic-tsv"},tmax_s=4)
