import pytest
from mindbench.alignment import align_trials, quality_summary
from mindbench.schema import ClockContract, ValidationError


def test_one_to_one_and_next_event_boundary():
    events = [{"onset": 1.0, "trial_type": "a"}, {"onset": 1.35, "trial_type": "b"}, {"onset": 3.0, "trial_type": "b"}]
    behavior = [{"onset": 1.42, "response": "x"}, {"onset": 3.15, "response": "y"}]
    out = align_trials(events, behavior, ClockContract(behavior_origin="acquisition_start"), eeg_duration_s=5)
    assert out[0].response is None
    assert out[1].response == "x"
    assert out[2].response == "y"
    assert len({t.response_s for t in out if t.response_s is not None}) == 2


def test_unverified_clock_cannot_match():
    out = align_trials([{"onset": 0.2, "trial_type": "a"}], [{"onset": 0.4, "response": "x"}],
                       ClockContract(), eeg_duration_s=2)
    assert out[0].response is None
    assert "behavior_clock_unverified" in out[0].flags


def test_artifact_missing_modalities_and_bounds():
    events = [{"onset": .1, "trial_type": "a"}, {"onset": .9, "trial_type": "b"}]
    out = align_trials(events, None, ClockContract(), eeg_duration_s=1.0,
                       artifact_intervals=[(.1, .2)])
    assert "eeg_artifact_overlap" in out[0].flags
    assert "epoch_out_of_eeg_range" in out[1].flags
    assert quality_summary(out)["with_behavior"] == 0
    assert quality_summary(out)["flags"]["behavior_missing"] == 2


def test_eeg_missing_and_invalid_ranges():
    out = align_trials([{"onset": 2., "trial_type": "a"}], None, ClockContract(), eeg_duration_s=None)
    assert "eeg_missing" in out[0].flags
    with pytest.raises(ValidationError):
        align_trials([{"onset": 0., "trial_type": "a"}], None, ClockContract(), eeg_duration_s=1.,
                     artifact_intervals=[(1, -2)])
    with pytest.raises(ValidationError):
        align_trials([{"onset": 1., "trial_type": "a"}, {"onset": .5, "trial_type": "b"}],
                     None, ClockContract(), eeg_duration_s=3.)
