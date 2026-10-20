"""Manifest v1, rights gate, content hashes and conservative clock audit."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .adapters import read_behavior, read_edf, read_events, read_synthetic_eeg
from .io import read_json, safe_input, sha256_file
from .schema import ClockContract, ResourceLimits, Rights, SCHEMA_VERSION, SubjectSession, ValidationError


def _source_file(root: Path, relative: Path, limits: ResourceLimits) -> tuple[Path, dict[str, Any]]:
    path = safe_input(root, relative, limits.max_file_bytes)
    return path, {"path": relative.as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def audit_run(root: Path, identity: SubjectSession, limits: ResourceLimits | None = None) -> dict[str, Any]:
    """Audit one run in a non-recursive path; do not export raw patient data.

    Every dataset must provide a root `rights.json` as a rights attestation.
    No automated external copyright/license verification is implied.
    """
    limits = limits or ResourceLimits()
    root = root.resolve(strict=True)
    files: list[dict[str, Any]] = []
    rights_path, provenance = _source_file(root, Path("rights.json"), limits)
    files.append(provenance)
    rights_data = read_json(rights_path)
    try:
        rights = Rights(**rights_data)
    except TypeError as exc:
        raise ValidationError(f"Invalid rights.json schema: {exc}") from exc

    clock_path, provenance = _source_file(root, Path("clock.json"), limits)
    files.append(provenance)
    try:
        clock = ClockContract(**read_json(clock_path))
    except TypeError as exc:
        raise ValidationError(f"Invalid clock.json schema: {exc}") from exc

    directory = identity.relative_dir()
    stem = identity.prefix()
    metadata_path, provenance = _source_file(root, directory / f"{stem}_eeg.json", limits)
    files.append(provenance)
    metadata = read_json(metadata_path)
    if "SamplingFrequency" not in metadata:
        raise ValidationError("EEG metadata missing SamplingFrequency")
    try:
        sampling_hz = float(metadata["SamplingFrequency"])
    except (ValueError, TypeError) as exc:
        raise ValidationError("Invalid SamplingFrequency") from exc

    # Prefer a declared adapter, never infer real EEG quality from TSV fixtures.
    adapter = metadata.get("MindBenchAdapter")
    if adapter == "synthetic-tsv":
        if not rights.synthetic:
            raise ValidationError("Synthetic TSV EEG requires synthetic rights")
        eeg_path, provenance = _source_file(root, directory / f"{stem}_eeg.tsv", limits)
        eeg = read_synthetic_eeg(eeg_path, sampling_hz, limits)
    elif adapter == "edf-mne":
        eeg_path, provenance = _source_file(root, directory / f"{stem}_eeg.edf", limits)
        eeg = read_edf(eeg_path, limits)
        if abs(eeg.sampling_hz - sampling_hz) > 1e-6:
            raise ValidationError("EDF sampling rate disagrees with EEG sidecar")
    else:
        raise ValidationError("MindBenchAdapter must be synthetic-tsv or edf-mne")
    files.append(provenance)

    events_path, provenance = _source_file(root, directory / f"{stem}_events.tsv", limits)
    files.append(provenance)
    events = read_events(events_path, limits)

    behavior_path, provenance = _source_file(root, directory / f"{stem}_beh.tsv", limits)
    files.append(provenance)
    behavior = read_behavior(behavior_path, limits)

    duration_s = eeg.duration_seconds()
    beyond = [e for e in events if e["onset"] >= duration_s or e["onset"] + e["duration"] > duration_s]
    before = [e for e in events if e["onset"] < 0]
    out_of_range_behavior = (
        [b for b in behavior if b["onset"] < 0 or b["onset"] >= duration_s]
        if clock.behavior_origin == "acquisition_start" else None
    )
    tolerance_samples = [abs(e["onset"] * eeg.sampling_hz - round(e["onset"] * eeg.sampling_hz)) for e in events]
    warnings: list[str] = []
    if before:
        warnings.append("Negative BIDS event onsets: prior to EEG acquisition start")
    if beyond or out_of_range_behavior:
        warnings.append("Some events/responses lie outside stored EEG coverage")
    if clock.behavior_origin == "unverified":
        warnings.append("Behavior clock origin is unverified: do not treat event times as aligned")
    if not clock.hardware_synced:
        warnings.append("Hardware-level synchronization NOT demonstrated")
    if any(delta > 0.49 for delta in tolerance_samples):
        warnings.append("Unusual sample-onset rounding discrepancy")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "identity": asdict(identity),
        "rights": asdict(rights),
        "clock_contract": asdict(clock),
        "eeg": asdict(eeg) | {"duration_seconds": duration_s},
        "event_count": len(events),
        "behavior_count": len(behavior),
        "synchronization_audit": {
            "clock_basis": "acquisition-relative seconds",
            "hardware_sync_verified": False,  # always false until an independent evidence-backed contract exists
            "event_before_start": len(before),
            "event_after_end": len(beyond),
            "behavior_out_of_range": (len(out_of_range_behavior) if out_of_range_behavior is not None else None),
            "max_event_sample_rounding_error": max(tolerance_samples, default=0.0),
            "warnings": warnings,
        },
        "source_files": sorted(files, key=lambda x: x["path"]),
        "limitations": [
            "License record is supplied by importer; verify source rights independently before redistributing.",
            "Time origin is asserted by importer, not proven by triggers or calibration.",
            "No neurophysiological/clinical validity, preprocessing or modeling claim is made.",
            "Only summary stats are retained; no raw signal or identifiable subjects are exported.",
        ],
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return manifest | {"manifest_sha256": hashlib.sha256(encoded).hexdigest()}
