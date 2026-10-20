"""Conservative clock-aware, one-to-one stimulus/response pairing and QC.

One acquisition clock is an *assumption* until independently validated. The
implementation refuses to match events under an unknown behavioral origin.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Sequence

from .schema import ClockContract, ValidationError


@dataclass(frozen=True, slots=True)
class Trial:
    index: int
    onset_s: float
    trial_type: str
    response_s: float | None
    latency_s: float | None
    response: str | None
    eeg_available: bool
    behavior_available: bool
    valid: bool
    flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def align_trials(
    events: Sequence[dict[str, Any]],
    behavior: Sequence[dict[str, Any]] | None,
    clock: ClockContract,
    *,
    eeg_duration_s: float | None,
    max_latency_s: float = 1.0,
    epoch_start_s: float = 0.0,
    epoch_stop_s: float = 0.5,
    artifact_intervals: Sequence[tuple[float, float]] = (),
) -> list[Trial]:
    """Pair each event to at most one subsequent response within a trial window.

    Pairing is conservative: responses after the *next* stimulus are never
    assigned to the earlier event, regardless of max_latency_s. Invalid or
    absent EEG and responses become explicit flags, never silently imputed.
    """
    if not events:
        raise ValidationError("Cannot align an empty event sequence")
    if (not math.isfinite(max_latency_s) or max_latency_s <= 0 or
        not math.isfinite(epoch_start_s) or not math.isfinite(epoch_stop_s) or
        epoch_start_s >= epoch_stop_s):
        raise ValidationError("Invalid alignment windows")
    if eeg_duration_s is not None and (not math.isfinite(eeg_duration_s) or eeg_duration_s <= 0):
        raise ValidationError("Invalid EEG duration")
    for lo, hi in artifact_intervals:
        if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
            raise ValidationError("Artifact intervals must be finite, positive-length")
    prev = -math.inf
    for event in events:
        onset = float(event["onset"])
        if not math.isfinite(onset) or onset < prev or not str(event["trial_type"]).strip():
            raise ValidationError("Events must have finite ordered onsets and labels")
        prev = onset
    responses = list(behavior) if behavior is not None else []
    prev = -math.inf
    for response in responses:
        onset = float(response["onset"])
        if not math.isfinite(onset) or onset < prev:
            raise ValidationError("Responses must be ordered with finite onsets")
        prev = onset
    can_pair = clock.behavior_origin == "acquisition_start" and behavior is not None
    used = 0
    trials: list[Trial] = []
    for i, event in enumerate(events):
        start = float(event["onset"])
        next_start = float(events[i + 1]["onset"]) if i + 1 < len(events) else math.inf
        flags: list[str] = []
        if eeg_duration_s is None:
            flags.append("eeg_missing")
        elif start + epoch_start_s < 0 or start + epoch_stop_s > eeg_duration_s:
            flags.append("epoch_out_of_eeg_range")
        if any(start + epoch_start_s < hi and start + epoch_stop_s > lo for lo, hi in artifact_intervals):
            flags.append("eeg_artifact_overlap")
        if behavior is None:
            flags.append("behavior_missing")
        elif not can_pair:
            flags.append("behavior_clock_unverified")
        match: dict[str, Any] | None = None
        if can_pair:
            while used < len(responses) and float(responses[used]["onset"]) < start:
                used += 1
            if used < len(responses):
                ts = float(responses[used]["onset"])
                if start <= ts < next_start and ts - start <= max_latency_s:
                    match = responses[used]
                    used += 1
            if match is None:
                flags.append("response_unmatched")
        latency = float(match["onset"]) - start if match else None
        trials.append(Trial(
            index=i, onset_s=start, trial_type=str(event["trial_type"]),
            response_s=float(match["onset"]) if match else None,
            latency_s=latency, response=str(match["response"]) if match else None,
            eeg_available=eeg_duration_s is not None and "epoch_out_of_eeg_range" not in flags and "eeg_artifact_overlap" not in flags,
            behavior_available=match is not None,
            valid=(eeg_duration_s is not None or match is not None) and not any(
                f in flags for f in ("epoch_out_of_eeg_range", "eeg_artifact_overlap", "behavior_clock_unverified")
            ),
            flags=tuple(flags),
        ))
    return trials


def quality_summary(trials: Sequence[Trial]) -> dict[str, Any]:
    if not trials:
        raise ValidationError("No trials for QC")
    counts: dict[str, int] = {}
    for trial in trials:
        for flag in trial.flags:
            counts[flag] = counts.get(flag, 0) + 1
    return {
        "n_trials": len(trials),
        "n_valid": sum(t.valid for t in trials),
        "with_eeg": sum(t.eeg_available for t in trials),
        "with_behavior": sum(t.behavior_available for t in trials),
        "complete_modalities": sum(t.eeg_available and t.behavior_available for t in trials),
        "eeg_only": sum(t.eeg_available and not t.behavior_available for t in trials),
        "behavior_only": sum(t.behavior_available and not t.eeg_available for t in trials),
        "neither_modality": sum(not t.eeg_available and not t.behavior_available for t in trials),
        "flags": dict(sorted(counts.items())),
        "clock_verification": "not_independently_verified",
    }
