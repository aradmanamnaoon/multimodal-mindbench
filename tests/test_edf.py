"""Self-contained minimal *synthetic* EDF generator for adapter integration test.

EDF test file does not originate from any participant and is not an external dataset.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct

import pytest

from mindbench.audit import audit_run
from mindbench.schema import SubjectSession
from mindbench.synthetic import generate_fixture


def _field(value: str | int, width: int) -> bytes:
    value = str(value)
    assert len(value) <= width
    return value.encode("ascii").ljust(width, b" ")


def synthetic_edf(path: Path, *, records: int = 3, frequency: int = 100) -> None:
    ns = 2
    header = b"".join((
        _field("0", 8), _field("X", 80), _field("synthetic test only", 80),
        _field("01.01.85", 8), _field("12.00.00", 8), _field(256 + ns * 256, 8),
        _field("EDF+C", 44), _field(records, 8), _field(1, 8), _field(ns, 4),
    ))
    specs = [
        (["Cz", "Pz"], 16), (["synthetic", "synthetic"], 80), (["uV", "uV"], 8),
        (["-100", "-100"], 8), (["100", "100"], 8),
        (["-32768", "-32768"], 8), (["32767", "32767"], 8),
        (["", ""], 80), ([str(frequency), str(frequency)], 8), (["", ""], 32),
    ]
    header += b"".join(_field(value, width) for values, width in specs for value in values)
    assert len(header) == 256 + ns * 256
    with path.open("wb") as f:
        f.write(header)
        for second in range(records):
            for channel in range(ns):
                f.write(struct.pack("<" + "h" * frequency, *(100 * channel + (i % 50) for i in range(frequency))))


def test_real_edf_adapter_with_synthetic_recording(tmp_path: Path) -> None:
    pytest.importorskip("mne")
    root = generate_fixture(tmp_path / "input")
    identity = SubjectSession("01", "01", "oddball", "01")
    prefix = root / identity.relative_dir() / identity.prefix()
    tsv = prefix.parent / f"{identity.prefix()}_eeg.tsv"
    tsv.unlink()
    path = prefix.parent / f"{identity.prefix()}_eeg.edf"
    synthetic_edf(path)
    meta_path = prefix.parent / f"{identity.prefix()}_eeg.json"
    metadata = json.loads(meta_path.read_text())
    metadata["MindBenchAdapter"] = "edf-mne"
    meta_path.write_text(json.dumps(metadata))
    manifest = audit_run(root, identity)
    assert manifest["eeg"]["adapter"] == "edf-mne"
    assert manifest["eeg"]["n_samples"] == 300
    assert manifest["eeg"]["channels"] == ["Cz", "Pz"]
    assert abs(manifest["eeg"]["max_value"][0]) < 0.001


def test_edf_features_pipeline_uses_bounded_epoch_reads(tmp_path: Path) -> None:
    pytest.importorskip("mne")
    from mindbench.features import run_features

    root = generate_fixture(tmp_path / "input")
    identity = SubjectSession("01", "01", "oddball", "01")
    prefix = root / identity.relative_dir() / identity.prefix()
    (prefix.parent / f"{identity.prefix()}_eeg.tsv").unlink()
    synthetic_edf(prefix.parent / f"{identity.prefix()}_eeg.edf")
    meta_path = prefix.parent / f"{identity.prefix()}_eeg.json"
    metadata = json.loads(meta_path.read_text())
    metadata["MindBenchAdapter"] = "edf-mne"
    meta_path.write_text(json.dumps(metadata))
    rows, provenance = run_features(root, identity, {"standard": 0, "deviant": 1})
    assert len(rows) == 3
    assert all(row.eeg is not None and len(row.eeg) == 2 for row in rows)
    assert provenance["channels"] == ["Cz", "Pz"]
    assert provenance["hardware_sync_verified"] is False
