"""Audited event-window EEG and behavioral latency features from real/synthetic runs.

Only the first two *consistent, preselected* EEG channels are used, scaled to
microvolts. These per-window means are engineering reference features, not
validated ERP/PSD features. Never fit normalization on held-out subjects.
"""
from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
from typing import Any, Sequence

from .adapters import finite, read_behavior, read_events
from .alignment import Trial, align_trials, quality_summary
from .audit import audit_run
from .cohort import Example
from .io import read_json, safe_input, tsv_rows
from .schema import ClockContract, ResourceLimits, SubjectSession, ValidationError


def window_means(root: Path, identity: SubjectSession, trials: Sequence[Trial],
                 metadata: dict[str, Any], limits: ResourceLimits | None = None,
                 *, tmin_s: float = 0., tmax_s: float = .5) -> list[tuple[float, float] | None]:
    """Bounded-window two-channel feature extraction, synthetic TSV or lazy EDF.

    TSV is streamed once with prefix checkpoints, O(N*C + trials*C) time and
    O(trials*C) memory. EDF loads only the requested trial slices, never preload.
    """
    limits = limits or ResourceLimits()
    if not (math.isfinite(tmin_s) and math.isfinite(tmax_s) and 0 <= tmin_s < tmax_s <= 3):
        raise ValidationError("Epoch must be finite, positive, at most 3 seconds")
    if len(trials) > min(2048, limits.max_events):
        raise ValidationError("Too many trials for bounded extraction")
    hz = float(metadata["SamplingFrequency"])
    if not math.isfinite(hz) or hz <= 0:
        raise ValidationError("Invalid EEG sampling rate")
    stem = identity.prefix()
    directory = identity.relative_dir()
    target: list[tuple[int, int] | None] = []
    checkpoints: set[int] = set()
    for trial in trials:
        if not trial.eeg_available:
            target.append(None)
            continue
        a = round((trial.onset_s + tmin_s) * hz)
        b = round((trial.onset_s + tmax_s) * hz)
        if a < 0 or b <= a or b > limits.max_samples:
            target.append(None)
            continue
        target.append((a, b))
        checkpoints.update((a, b))
    result: list[tuple[float, float] | None] = [None] * len(trials)
    if not checkpoints:
        return result
    if metadata.get("MindBenchAdapter") == "synthetic-tsv":
        path = safe_input(root, directory / f"{stem}_eeg.tsv", limits.max_file_bytes)
        with path.open("r", encoding="utf-8") as stream:
            header = stream.readline().rstrip("\n\r").split("\t")
        if len(header) < 3 or len(header) != len(set(header)) or header[0] != "sample":
            raise ValidationError("Two unique EEG channel names needed")
        ch1, ch2 = header[1:3]
        cumulative = [0., 0.]
        snapshots: dict[int, tuple[float, float]] = {}
        count = 0
        for row in tsv_rows(path, set(header), limits.max_samples):
            if count in checkpoints:
                snapshots[count] = (cumulative[0], cumulative[1])
            if finite(row["sample"], "sample") != count:
                raise ValidationError("Non-contiguous sample indexing")
            cumulative[0] += finite(row[ch1], ch1)
            cumulative[1] += finite(row[ch2], ch2)
            count += 1
        if count in checkpoints:
            snapshots[count] = tuple(cumulative)
        for i, bounds in enumerate(target):
            if bounds is None:
                continue
            a, b = bounds
            if a not in snapshots or b not in snapshots:
                continue
            result[i] = ((snapshots[b][0] - snapshots[a][0]) / (b - a) * 1e6,
                         (snapshots[b][1] - snapshots[a][1]) / (b - a) * 1e6)
    elif metadata.get("MindBenchAdapter") == "edf-mne":
        try:
            import mne
        except ImportError as exc:
            raise ValidationError("EDF requires optional MNE in hosted compute") from exc
        path = safe_input(root, directory / f"{stem}_eeg.edf", limits.max_file_bytes)
        raw = mne.io.read_raw_edf(path, preload=False, verbose="ERROR")
        try:
            picks = mne.pick_types(raw.info, eeg=True, exclude=[])
            if len(picks) < 2 or abs(float(raw.info["sfreq"]) - hz) > 1e-6:
                raise ValidationError("Requires two EEG channels and matching declared sampling rate")
            for i, bounds in enumerate(target):
                if bounds is None:
                    continue
                a, b = bounds
                if b > raw.n_times:
                    continue
                data = raw.get_data(picks=picks[:2], start=a, stop=b)
                if not bool(math.isfinite(float(data.min()))) or not bool(math.isfinite(float(data.max()))):
                    raise ValidationError("Nonfinite EDF epoch")
                result[i] = (float(data[0].mean()) * 1e6, float(data[1].mean()) * 1e6)
        finally:
            raw.close()
    else:
        raise ValidationError("Unsupported source EEG adapter")
    return result


def run_features(root: Path, identity: SubjectSession, label_map: dict[str, int],
                 limits: ResourceLimits | None = None) -> tuple[list[Example], dict[str, Any]]:
    """An auditable (but *not* rights-independently-verified) run-to-feature bridge."""
    limits = limits or ResourceLimits()
    manifest = audit_run(root, identity, limits)
    stem, directory = identity.prefix(), identity.relative_dir()
    events = read_events(safe_input(root, directory / f"{stem}_events.tsv", limits.max_file_bytes), limits)
    behavior = read_behavior(safe_input(root, directory / f"{stem}_beh.tsv", limits.max_file_bytes), limits)
    clock = ClockContract(**read_json(safe_input(root, Path("clock.json"), limits.max_file_bytes)))
    aligned = align_trials(events, behavior, clock, eeg_duration_s=manifest["eeg"]["duration_seconds"])
    eeg_feats = window_means(root, identity, aligned, manifest["eeg"] | {"SamplingFrequency": manifest["eeg"]["sampling_hz"],
                                                                 "MindBenchAdapter": manifest["eeg"]["adapter"]}, limits)
    if any(event["trial_type"] not in label_map or label_map[event["trial_type"]] not in (0, 1) for event in events):
        raise ValidationError("All trial types must map explicitly to binary 0 or 1")
    items = [Example(sample_id=f"{identity.prefix()}-t{i:04d}", subject=identity.subject,
                     session=identity.session, label=label_map[trial.trial_type],
                     eeg=eeg_feats[i], behavior=(trial.latency_s, trial.latency_s**2) if trial.latency_s is not None else None)
             for i, trial in enumerate(aligned)]
    return items, {"manifest_sha256": manifest["manifest_sha256"], "qc": quality_summary(aligned),
                   "channels": manifest["eeg"]["channels"][:2], "feature_units": ["microvolts", "microvolts", "s", "s_squared"],
                   "labels": dict(label_map), "hardware_sync_verified": False,
                   "rights_independently_verified": False}
