"""Bounded EEG + BIDS event and behavioral TSV adapters.

A synthetic EEG TSV format is explicitly NOT a BIDS-standard raw EEG format.
EDF can be ingested through optional MNE without loading the whole recording.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

from .io import tsv_rows
from .schema import ResourceLimits, ValidationError


def finite(value: str, field: str) -> float:
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Non-numeric {field}") from None
    if not math.isfinite(number):
        raise ValidationError(f"Non-finite {field}")
    return number


@dataclass(frozen=True)
class EEGSummary:
    adapter: str
    sampling_hz: float
    channels: list[str]
    n_samples: int
    sample_range: list[int]
    min_value: list[float]
    max_value: list[float]
    # The EDF path emits MNE internal SI units (usually volts for EEG).
    units: str

    def duration_seconds(self) -> float:
        return self.n_samples / self.sampling_hz


def read_synthetic_eeg(path: Path, sampling_hz: float, limits: ResourceLimits) -> EEGSummary:
    if sampling_hz <= 0 or not math.isfinite(sampling_hz):
        raise ValidationError("Invalid EEG sampling rate")
    with path.open("r", encoding="utf-8") as f:
        header = f.readline().rstrip("\n\r").split("\t")
    if len(header) < 2 or header[0] != "sample" or len(header) != len(set(header)):
        raise ValidationError("Synthetic EEG header requires sample and unique channels")
    channels = header[1:]
    if len(channels) > limits.max_channels:
        raise ValidationError("Too many EEG channels")
    if any(not s or s.isspace() for s in channels):
        raise ValidationError("Empty EEG channel label")
    minimum = [math.inf] * len(channels)
    maximum = [-math.inf] * len(channels)
    count = 0
    for row in tsv_rows(path, set(header), limits.max_samples):
        index = finite(row["sample"], "sample")
        if not index.is_integer() or int(index) != count:
            raise ValidationError(f"EEG samples must be contiguous from zero; observed {index}")
        for i, label in enumerate(channels):
            value = finite(row[label], f"EEG {label}")
            minimum[i] = min(minimum[i], value)
            maximum[i] = max(maximum[i], value)
        count += 1
    if count == 0:
        raise ValidationError("EEG has zero samples")
    return EEGSummary("synthetic-tsv", sampling_hz, channels, count, [0, count - 1], minimum, maximum, "volts")


def read_edf(path: Path, limits: ResourceLimits) -> EEGSummary:
    try:
        import mne  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValidationError("EDF ingest needs optional mne; install mindbench[edf] in hosted CI") from exc
    try:
        raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
    except (OSError, ValueError, RuntimeError) as exc:
        raise ValidationError(f"EDF format error: {exc}") from exc
    try:
        picks = mne.pick_types(raw.info, eeg=True, exclude=[])
        if len(picks) == 0 or len(picks) > limits.max_channels:
            raise ValidationError("EDF requires 1..max_channels EEG channels")
        if raw.n_times == 0 or raw.n_times > limits.max_samples:
            raise ValidationError("EDF sample limit exceeded or empty")
        minimum = [math.inf] * len(picks)
        maximum = [-math.inf] * len(picks)
        for start in range(0, raw.n_times, limits.edf_chunk_samples):
            stop = min(raw.n_times, start + limits.edf_chunk_samples)
            block = raw.get_data(picks=picks, start=start, stop=stop)
            if not bool(math.isfinite(float(block.min()))) or not bool(math.isfinite(float(block.max()))):
                raise ValidationError("EDF contains non-finite signal values")
            for index, signal in enumerate(block):
                minimum[index] = min(minimum[index], float(signal.min()))
                maximum[index] = max(maximum[index], float(signal.max()))
        return EEGSummary("edf-mne", float(raw.info["sfreq"]), [raw.ch_names[p] for p in picks], int(raw.n_times), [0, int(raw.n_times) - 1], minimum, maximum, "SI (MNE)")
    finally:
        raw.close()


def read_events(path: Path, limits: ResourceLimits) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    last = -math.inf
    for row in tsv_rows(path, {"onset", "duration", "trial_type"}, limits.max_events):
        onset = finite(row["onset"], "event onset")
        duration = finite(row["duration"], "event duration")
        if duration < 0:
            raise ValidationError("Event durations cannot be negative")
        if onset < last:
            raise ValidationError("Event onsets must be ordered ascending")
        if not row["trial_type"].strip():
            raise ValidationError("Event trial_type is empty")
        events.append({"onset": onset, "duration": duration, "trial_type": row["trial_type"]})
        last = onset
    if not events:
        raise ValidationError("No events in EEG task")
    return events


def read_behavior(path: Path, limits: ResourceLimits) -> list[dict[str, Any]]:
    behavior: list[dict[str, Any]] = []
    last = -math.inf
    for row in tsv_rows(path, {"onset", "response"}, limits.max_events):
        onset = finite(row["onset"], "behavior onset")
        if onset < last:
            raise ValidationError("Behavior onsets must be ordered ascending")
        if not row["response"].strip():
            raise ValidationError("Behavior response is empty")
        behavior.append({"onset": onset, "response": row["response"]})
        last = onset
    return behavior
