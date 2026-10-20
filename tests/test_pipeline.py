from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mindbench.audit import audit_run
from mindbench.cli import main
from mindbench.io import sha256_file, safe_input
from mindbench.report import html_report
from mindbench.schema import ClockContract, ResourceLimits, Rights, SubjectSession, ValidationError
from mindbench.synthetic import generate_fixture


@pytest.fixture
def sample(tmp_path: Path) -> tuple[Path, SubjectSession]:
    root = tmp_path / "data"
    identity = SubjectSession("01", "01", "oddball", "01")
    generate_fixture(root, identity)
    return root, identity


def input_file(root: Path, identity: SubjectSession, suffix: str) -> Path:
    return root / identity.relative_dir() / f"{identity.prefix()}{suffix}"


def test_fixture_end_to_end(sample):
    root, identity = sample
    manifest = audit_run(root, identity)
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["rights"]["synthetic"] is True
    assert manifest["eeg"]["n_samples"] == 300
    assert manifest["eeg"]["channels"] == ["Cz", "Pz"]
    assert manifest["event_count"] == 3
    assert manifest["behavior_count"] == 3
    assert manifest["synchronization_audit"]["hardware_sync_verified"] is False
    assert len(manifest["source_files"]) == 6
    assert all(len(f["sha256"]) == 64 for f in manifest["source_files"])


def test_deterministic_manifest(sample):
    root, identity = sample
    assert audit_run(root, identity)["manifest_sha256"] == audit_run(root, identity)["manifest_sha256"]


def test_license_missing_and_not_allowlisted(sample):
    root, identity = sample
    (root / "rights.json").unlink()
    with pytest.raises(FileNotFoundError):
        audit_run(root, identity)
    generate_fixture(root.parent / "second")
    other = root.parent / "second"
    rights = json.loads((other / "rights.json").read_text())
    rights["license"] = "unlicensed"
    (other / "rights.json").write_text(json.dumps(rights))
    with pytest.raises(ValidationError, match="license"):
        audit_run(other, identity)


def test_rights_mismatch():
    with pytest.raises(ValidationError, match="disagree"):
        Rights("CC0-1.0", "https://example.org", "ds", "1", "citation", "reviewer", True)
    with pytest.raises(ValidationError, match="HTTPS"):
        Rights("CC0-1.0", "file:///tmp/raw", "ds", "1", "citation", "reviewer", False)


def test_bad_identity_and_clock():
    with pytest.raises(ValidationError):
        SubjectSession("../escape", "1", "task", "1")
    with pytest.raises(ValidationError):
        ClockContract(behavior_origin="unverified", hardware_synced=True)


@pytest.mark.parametrize("sample_value", ["0", "2", "3.5", "NaN", "inf", "-1"])
def test_noncontiguous_eeg_rejected(sample, sample_value):
    root, identity = sample
    f = input_file(root, identity, "_eeg.tsv")
    text = f.read_text().splitlines()
    text[2] = sample_value + "\t0.0\t0.0"
    f.write_text("\n".join(text) + "\n")
    with pytest.raises(ValidationError):
        audit_run(root, identity)


def test_sample_bound_enforced(sample):
    root, identity = sample
    with pytest.raises(ValidationError, match="rows exceed"):
        audit_run(root, identity, ResourceLimits(max_samples=10))


def test_byte_bound_enforced(sample):
    root, identity = sample
    with pytest.raises(ValidationError, match="File exceeds"):
        audit_run(root, identity, ResourceLimits(max_file_bytes=200))


def test_tsv_duplicate_columns(sample):
    root, identity = sample
    f = input_file(root, identity, "_events.tsv")
    f.write_text("onset\tduration\ttrial_type\tonset\n0\t0.1\ta\t0\n")
    with pytest.raises(ValidationError, match="columns"):
        audit_run(root, identity)


def test_events_nonmonotonic(sample):
    root, identity = sample
    f = input_file(root, identity, "_events.tsv")
    f.write_text("onset\tduration\ttrial_type\n2\t0.1\ta\n1\t0.1\tb\n")
    with pytest.raises(ValidationError, match="ordered"):
        audit_run(root, identity)


def test_events_negative_duration(sample):
    root, identity = sample
    f = input_file(root, identity, "_events.tsv")
    f.write_text("onset\tduration\ttrial_type\n1\t-0.1\ta\n")
    with pytest.raises(ValidationError, match="duration"):
        audit_run(root, identity)


def test_unverified_clock_warning(sample):
    root, identity = sample
    (root / "clock.json").write_text('{"behavior_origin":"unverified"}')
    manifest = audit_run(root, identity)
    assert "unverified" in " ".join(manifest["synchronization_audit"]["warnings"])
    assert manifest["synchronization_audit"]["behavior_out_of_range"] is None


def test_audit_flags_outside_coverage(sample):
    root, identity = sample
    f = input_file(root, identity, "_events.tsv")
    f.write_text("onset\tduration\ttrial_type\n-1\t0.2\ta\n3\t0.2\tb\n")
    audit = audit_run(root, identity)["synchronization_audit"]
    assert audit["event_before_start"] == 1
    assert audit["event_after_end"] == 1


def test_path_traversal_and_symlink(sample, tmp_path):
    root, _ = sample
    with pytest.raises(ValidationError, match="Invalid input path"):
        safe_input(root, Path("../evil"), 20)
    (root / "linked.json").symlink_to(root / "rights.json")
    with pytest.raises(ValidationError, match="Symlink"):
        safe_input(root, Path("linked.json"), 2000)


def test_cli_and_html_escaping(tmp_path, sample):
    root, identity = sample
    out = tmp_path / "out"
    assert main(["audit", "--root", str(root), "--output", str(out), "--subject", identity.subject,
                 "--session", identity.session, "--task", identity.task, "--run", identity.run]) == 0
    assert (out / "manifest.json").exists()
    report = (out / "report.html").read_text()
    assert '<html lang="en">' in report
    manifest = audit_run(root, identity)
    unsafe = copy.deepcopy(manifest)
    unsafe["rights"]["dataset_id"] = "<script>alert(1)</script>"
    text = html_report(unsafe)
    assert "&lt;script&gt;" in text
    assert "<script>" not in text


def test_cli_fails_safe(tmp_path, capsys):
    assert main(["audit", "--root", str(tmp_path), "--output", str(tmp_path / "out"),
                 "--subject", "1", "--session", "1", "--task", "task", "--run", "1"]) == 2
    assert "mindbench:" in capsys.readouterr().err


def test_symlink_does_not_leak(sample):
    root, identity = sample
    f = input_file(root, identity, "_eeg.tsv")
    original = f.read_text()
    f.unlink()
    f.symlink_to(root / "rights.json")
    with pytest.raises(ValidationError, match="Symlink"):
        audit_run(root, identity)
    assert len(original) > 0
