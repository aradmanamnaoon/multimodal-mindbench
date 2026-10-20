"""Deterministic, exclusively simulated features for engineering benchmarks.

These features are *not* measurements from EEG instruments or participants.
The generator intentionally supports domain shift, missingness, and weak signal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Any

from .schema import ValidationError


@dataclass(frozen=True, slots=True)
class Example:
    sample_id: str
    subject: str
    session: str
    label: int
    eeg: tuple[float, float] | None
    behavior: tuple[float, float] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def synthetic_cohort(*, n_subjects: int = 24, trials_per_subject: int = 30,
                     seed: int = 2026, missing_rate: float = 0.12) -> list[Example]:
    if n_subjects < 6 or not 4 <= trials_per_subject <= 500 or not 0 <= missing_rate <= 0.4:
        raise ValidationError("Synthetic cohort configuration invalid")
    rng = random.Random(seed)
    examples: list[Example] = []
    for sid in range(n_subjects):
        subject = f"s{sid + 1:03d}"
        baseline = rng.gauss(0, 0.65)
        site_shift = 0.35 if sid % 3 == 0 else -0.15
        for trial in range(trials_per_subject):
            label = trial % 2
            # Shuffle label within subject without letting subject ID predict class.
            if rng.random() < 0.5:
                label = 1 - label
            latent = (label * 2 - 1) * 0.6
            eeg = (latent + baseline + site_shift + rng.gauss(0, 1.1),
                   0.5 * latent + rng.gauss(0, 0.85))
            behavior = (0.58 - 0.13 * label + 0.045 * baseline + rng.gauss(0, 0.18),
                        rng.gauss(0.4 * latent, 0.9))
            if rng.random() < missing_rate:
                eeg = None
            if rng.random() < missing_rate:
                behavior = None
            examples.append(Example(
                sample_id=f"{subject}-t{trial:03d}", subject=subject,
                session="01", label=label, eeg=eeg, behavior=behavior,
            ))
    return examples
