"""Strict provenance, identity and ingest configuration models.

This application records asserted acquisition clocks but does not establish
hardware synchronization. It deliberately rejects absent rights evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit
from typing import Literal

SCHEMA_VERSION = "1.0.0"
ALLOWED_RIGHTS = frozenset({"CC0-1.0", "CC-BY-4.0", "synthetic"})
_BIDS_LABEL = re.compile(r"^[A-Za-z0-9]+$")


class ValidationError(ValueError):
    """Input fails a scientific, license or resource invariant."""


def bids_label(value: str, field: str) -> str:
    if not _BIDS_LABEL.fullmatch(value):
        raise ValidationError(f"Invalid {field}: expected ASCII alphanumerics")
    return value


@dataclass(frozen=True, slots=True)
class SubjectSession:
    subject: str
    session: str
    task: str
    run: str

    def __post_init__(self) -> None:
        for key in ("subject", "session", "task", "run"):
            bids_label(getattr(self, key), key)

    def prefix(self) -> str:
        return f"sub-{self.subject}_ses-{self.session}_task-{self.task}_run-{self.run}"

    def relative_dir(self) -> Path:
        return Path(f"sub-{self.subject}") / f"ses-{self.session}" / "eeg"


@dataclass(frozen=True, slots=True)
class Rights:
    license: str
    source_url: str
    dataset_id: str
    dataset_version: str
    citation: str
    attested_by: str
    synthetic: bool

    def __post_init__(self) -> None:
        if not isinstance(self.license, str) or self.license not in ALLOWED_RIGHTS:
            raise ValidationError("Dataset license is not explicitly allowlisted")
        if type(self.synthetic) is not bool:
            raise ValidationError("Rights synthetic field must be a JSON boolean")
        if self.synthetic != (self.license == "synthetic"):
            raise ValidationError("Synthetic status and declared license disagree")
        for name in ("dataset_id", "dataset_version", "citation", "attested_by"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValidationError(f"Required rights field: {name}")
        if not isinstance(self.source_url, str):
            raise ValidationError("Rights source must be a URL string")
        try:
            parsed = urlsplit(self.source_url)
            valid = (parsed.scheme == "https" and bool(parsed.hostname) and not self.synthetic) or (
                self.synthetic and parsed.scheme == "synthetic" and bool(parsed.netloc)
            )
        except ValueError:
            valid = False
        if not valid or any(ord(c) < 32 for c in self.source_url):
            raise ValidationError("Rights source must be an HTTPS URL or synthetic:// identifier")


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    max_file_bytes: int = 128 * 1024 * 1024
    max_samples: int = 1_000_000
    max_events: int = 100_000
    max_channels: int = 256
    edf_chunk_samples: int = 4096

    def __post_init__(self) -> None:
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            raise ValidationError("Resource limits must be positive integers")


@dataclass(frozen=True, slots=True)
class ClockContract:
    # Acquisition-relative clocks for EEG and behavioral events.
    eeg_origin: Literal["acquisition_start"] = "acquisition_start"
    behavior_origin: Literal["acquisition_start", "unverified"] = "unverified"
    hardware_synced: bool = False

    def __post_init__(self) -> None:
        if self.eeg_origin != "acquisition_start" or self.behavior_origin not in ("acquisition_start", "unverified"):
            raise ValidationError("Unsupported acquisition clock origin")
        if type(self.hardware_synced) is not bool:
            raise ValidationError("Hardware synchronization flag must be a JSON boolean")
        if self.hardware_synced and self.behavior_origin != "acquisition_start":
            raise ValidationError("Hardware sync cannot be claimed with an unverified behavioral clock")
