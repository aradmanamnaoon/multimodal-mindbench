"""Fully synthetic fixture generator; no human participant data."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .schema import SubjectSession, ValidationError


def generate_fixture(root: Path, identity: SubjectSession | None = None, *, samples: int = 300, sampling_hz: int = 100) -> Path:
    identity = identity or SubjectSession("01", "01", "oddball", "01")
    if not (10 <= samples <= 10_000 and 1 <= sampling_hz <= 2048):
        raise ValidationError("Fixture samples or frequency outside supported range")
    if root.exists() and any(root.iterdir()):
        raise ValidationError("Synthetic fixture target must be empty")
    root.mkdir(parents=True, exist_ok=True)
    relative = identity.relative_dir()
    directory = root / relative
    directory.mkdir(parents=True, exist_ok=True)
    stem = identity.prefix()
    (root / "rights.json").write_text(json.dumps({
        "license": "synthetic", "source_url": "synthetic://mindbench/v1",
        "dataset_id": "mindbench-synthetic-oddball", "dataset_version": "1.0.0",
        "citation": "Multimodal MindBench synthetic fixture generator v1 (no human data)",
        "attested_by": "software-generated", "synthetic": True,
    }, indent=2) + "\n", encoding="utf-8")
    (root / "clock.json").write_text(json.dumps({
        "eeg_origin": "acquisition_start", "behavior_origin": "acquisition_start",
        "hardware_synced": False,
    }, indent=2) + "\n", encoding="utf-8")
    (directory / f"{stem}_eeg.json").write_text(json.dumps({
        "SamplingFrequency": sampling_hz, "MindBenchAdapter": "synthetic-tsv",
        "EEGReference": "synthetic-idealized", "EEGGround": "n/a",
        "PowerLineFrequency": "n/a",
    }, indent=2) + "\n", encoding="utf-8")
    with (directory / f"{stem}_eeg.tsv").open("w", encoding="utf-8", newline="") as f:
        f.write("sample\tCz\tPz\n")
        for i in range(samples):
            t = i / sampling_hz
            f.write(f"{i}\t{1e-6 * math.sin(2 * math.pi * 8 * t):.12g}\t{0.7e-6 * math.sin(2 * math.pi * 12 * t):.12g}\n")
    max_onset = max(0, int(samples / sampling_hz) - 1)
    with (directory / f"{stem}_events.tsv").open("w", encoding="utf-8") as f:
        f.write("onset\tduration\ttrial_type\n")
        for t in range(max_onset + 1):
            f.write(f"{t + 0.1:.3f}\t0.1\t{'deviant' if t % 2 else 'standard'}\n")
    with (directory / f"{stem}_beh.tsv").open("w", encoding="utf-8") as f:
        f.write("onset\tresponse\n")
        for t in range(max_onset + 1):
            f.write(f"{t + 0.3:.3f}\t{'yes' if t % 2 else 'no'}\n")
    return root
